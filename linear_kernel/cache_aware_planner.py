"""Cache-aware rule baseline for backend and block-width selection."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from .cache_profile import CacheProfile, estimate_block_lut_bytes, get_cache_profile
from .matrix_utils import require_gf2_matrix


@dataclass(frozen=True)
class CacheAwareSelection:
    """One explained cache-aware planner decision."""

    selected_backend: str
    selected_block_width: int
    lut_bytes: int
    fits_l1: bool
    fits_l2: bool
    fits_l3: bool
    uses_lut: bool
    cache_fit_applicable: bool
    selection_reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class CacheAwarePlanner:
    """Small rule-based planner that uses LUT footprint and cache metadata.

    This is a deterministic baseline for experiments. It is not an optimal
    scheduler and does not use benchmark results when making decisions.
    """

    def __init__(
        self,
        matrix: np.ndarray,
        *,
        cache_profile: CacheProfile | None = None,
        block_width_candidates: tuple[int, ...] = (4, 6, 8, 10),
        sparse_threshold: int = 8,
        batch_threshold: int = 64,
    ) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape
        self.cache_profile = cache_profile or get_cache_profile()
        self.block_width_candidates = tuple(int(width) for width in block_width_candidates)
        if not self.block_width_candidates:
            raise ValueError("block_width_candidates must not be empty")
        if any(width <= 0 for width in self.block_width_candidates):
            raise ValueError("block_width_candidates must be positive")
        self.sparse_threshold = int(sparse_threshold)
        self.batch_threshold = int(batch_threshold)
        self.small_batch_threshold = 16
        if self.sparse_threshold < 0:
            raise ValueError("sparse_threshold must be non-negative")
        if self.batch_threshold < 1:
            raise ValueError("batch_threshold must be positive")
        self.packed_word_bits = 16 if self.r <= 16 else 32
        if self.r > self.packed_word_bits:
            raise ValueError("CacheAwarePlanner currently supports r <= 32")

    def select(self, workload: dict[str, Any]) -> CacheAwareSelection:
        """Return an explained backend/block-width selection."""
        workload_type = str(workload.get("type", "")).strip()
        output_mode = str(workload.get("output_mode", "unpacked")).strip()
        batch_size = int(workload.get("batch_size", 1))
        candidate_count = int(workload.get("candidate_count", batch_size))

        if workload_type == "event_update":
            return self._non_lut_selection(
                "EventUpdateKernel",
                "event update workload uses incremental syndrome updates",
            )

        if workload_type in {"single", "sparse_single"}:
            hamming_weight = int(workload.get("hamming_weight", 0))
            if hamming_weight <= self.sparse_threshold:
                return self._non_lut_selection(
                    "SparseXorKernel",
                    f"sparse single input hamming_weight={hamming_weight} <= {self.sparse_threshold}",
                )
            return self._lut_selection(
                "dense single input uses packed LUT when cache footprint is acceptable",
            )

        lut = self._best_lut_candidate(
            candidate_count=candidate_count,
            workload_type=workload_type,
            batch_size=batch_size,
        )

        if workload_type == "candidate_test_packed":
            if candidate_count >= self.small_batch_threshold and lut["fits_l3"]:
                return self._lut_selection(
                    "large packed candidate batch uses LUT selected by cache footprint",
                    lut,
                )
            return self._non_lut_selection(
                "PackedBatchGF2Kernel",
                "candidate batch LUT does not fit cache target or batch is small; use vectorized fallback",
            )

        if workload_type in {"dense_batch", "component_decode_batch", "batch"}:
            workload_label = workload_type.replace("_", " ")
            if batch_size < self.small_batch_threshold:
                return self._non_lut_selection(
                    "PackedBatchGF2Kernel",
                    (
                        f"small {workload_label} batch_size={batch_size} avoids LUT "
                        "setup/mask overhead"
                    ),
                )
            if output_mode == "packed":
                if lut["fits_l3"]:
                    return self._lut_selection(
                        "packed batch output uses LUT selected by cache footprint",
                        lut,
                    )
                return self._non_lut_selection(
                    "PackedBatchGF2Kernel",
                    "packed LUT footprint does not fit L3; use vectorized fallback plus packing",
                )
            if lut["fits_l2"] or lut["fits_l3"]:
                cache_level = "L2" if lut["fits_l2"] else "L3"
                return self._lut_selection(
                    (
                        f"{workload_label} batch_size={batch_size} uses packed LUT "
                        f"because selected table fits {cache_level}; unpacked output "
                        "does not force vectorized fallback"
                    ),
                    lut,
                )
            return self._non_lut_selection(
                "PackedBatchGF2Kernel",
                "selected LUT does not fit L3 for unpacked batch; use vectorized fallback",
            )

        if lut["fits_l2"]:
            return self._lut_selection("default selection uses LUT fitting L2", lut)
        return self._non_lut_selection("PackedBatchGF2Kernel", "default vectorized fallback")

    def _best_lut_candidate(
        self,
        *,
        candidate_count: int | None = None,
        workload_type: str = "",
        batch_size: int = 1,
    ) -> dict[str, Any]:
        estimates = [
            {
                "block_width": width,
                **estimate_block_lut_bytes(
                    n=self.n,
                    r=self.r,
                    block_width=width,
                    packed_word_bits=self.packed_word_bits,
                    cache_profile=self.cache_profile,
                ),
            }
            for width in self.block_width_candidates
        ]
        candidate_count = 0 if candidate_count is None else int(candidate_count)
        workload_type = str(workload_type)
        batch_size = int(batch_size)
        fitting_l3 = [estimate for estimate in estimates if estimate["fits_l3"]]

        if workload_type == "candidate_test_packed" and fitting_l3:
            if candidate_count >= 8192:
                return self._prefer_exact_width(fitting_l3, preferred_width=6)
            if candidate_count >= 16:
                return self._prefer_widest_bounded(fitting_l3, max_width=12)

        if workload_type in {"dense_batch", "component_decode_batch", "batch"} and fitting_l3:
            if batch_size >= 8192:
                return self._prefer_exact_width(fitting_l3, preferred_width=6)
            if batch_size >= 16 and batch_size <= 64:
                return self._prefer_widest_bounded(fitting_l3, max_width=12)

        fitting_l1 = [estimate for estimate in estimates if estimate["fits_l1"]]
        if fitting_l1:
            return self._prefer_stable_width(fitting_l1, preferred_width=8)
        fitting_l2 = [estimate for estimate in estimates if estimate["fits_l2"]]
        if fitting_l2:
            if candidate_count >= 16_384:
                wider = [
                    estimate
                    for estimate in fitting_l2
                    if int(estimate["block_width"]) in {10, 12}
                ]
                if wider:
                    return min(wider, key=lambda estimate: int(estimate["lut_bytes"]))
            return self._prefer_stable_width(fitting_l2, preferred_width=8)
        if fitting_l3:
            return self._prefer_stable_width(fitting_l3, preferred_width=8)
        return min(estimates, key=lambda estimate: int(estimate["lut_bytes"]))

    @staticmethod
    def _prefer_exact_width(
        estimates: list[dict[str, Any]],
        *,
        preferred_width: int,
    ) -> dict[str, Any]:
        preferred = [
            estimate
            for estimate in estimates
            if int(estimate["block_width"]) == preferred_width
        ]
        if preferred:
            return preferred[0]
        return CacheAwarePlanner._prefer_stable_width(
            estimates,
            preferred_width=min(preferred_width, 8),
        )

    @staticmethod
    def _prefer_widest_bounded(
        estimates: list[dict[str, Any]],
        *,
        max_width: int,
    ) -> dict[str, Any]:
        bounded = [
            estimate
            for estimate in estimates
            if int(estimate["block_width"]) <= max_width
        ]
        if bounded:
            return max(bounded, key=lambda estimate: int(estimate["block_width"]))
        return min(estimates, key=lambda estimate: int(estimate["lut_bytes"]))

    @staticmethod
    def _prefer_stable_width(
        estimates: list[dict[str, Any]],
        *,
        preferred_width: int,
    ) -> dict[str, Any]:
        preferred = [
            estimate
            for estimate in estimates
            if int(estimate["block_width"]) == preferred_width
        ]
        if preferred:
            return preferred[0]
        narrower = [
            estimate
            for estimate in estimates
            if int(estimate["block_width"]) < preferred_width
        ]
        if narrower:
            return max(narrower, key=lambda estimate: int(estimate["block_width"]))
        return min(estimates, key=lambda estimate: int(estimate["lut_bytes"]))

    def _lut_selection(
        self,
        reason: str,
        lut: dict[str, Any] | None = None,
    ) -> CacheAwareSelection:
        lut = lut or self._best_lut_candidate()
        return CacheAwareSelection(
            selected_backend="PackedBlockLUTKernel",
            selected_block_width=int(lut["block_width"]),
            lut_bytes=int(lut["lut_bytes"]),
            fits_l1=bool(lut["fits_l1"]),
            fits_l2=bool(lut["fits_l2"]),
            fits_l3=bool(lut["fits_l3"]),
            uses_lut=True,
            cache_fit_applicable=True,
            selection_reason=reason,
        )

    def _non_lut_selection(self, backend: str, reason: str) -> CacheAwareSelection:
        return CacheAwareSelection(
            selected_backend=backend,
            selected_block_width=0,
            lut_bytes=0,
            fits_l1=False,
            fits_l2=False,
            fits_l3=False,
            uses_lut=False,
            cache_fit_applicable=False,
            selection_reason=reason,
        )
