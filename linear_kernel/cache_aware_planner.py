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

        lut = self._best_lut_candidate()

        if workload_type == "candidate_test_packed":
            if candidate_count >= self.batch_threshold and lut["fits_l3"]:
                return self._lut_selection(
                    "large packed candidate batch uses LUT selected by cache footprint",
                    lut,
                )
            return self._non_lut_selection(
                "PackedBatchGF2Kernel",
                "candidate batch LUT does not fit cache target or batch is small; use vectorized fallback",
            )

        if workload_type in {"dense_batch", "component_decode_batch", "batch"}:
            if output_mode == "packed":
                if lut["fits_l3"]:
                    return self._lut_selection("packed batch output requires packed LUT path", lut)
                return self._non_lut_selection(
                    "PackedBatchGF2Kernel",
                    "packed LUT footprint does not fit L3; use vectorized fallback plus packing",
                )
            if batch_size >= self.batch_threshold:
                return self._non_lut_selection(
                    "PackedBatchGF2Kernel",
                    f"large unpacked batch_size={batch_size} uses vectorized PackedBatch path",
                )
            if lut["fits_l2"]:
                return self._lut_selection(
                    "small/dense batch uses packed LUT because selected table fits L2",
                    lut,
                )
            return self._non_lut_selection(
                "PackedBatchGF2Kernel",
                "selected LUT does not fit L2 for unpacked batch; use vectorized fallback",
            )

        if lut["fits_l2"]:
            return self._lut_selection("default selection uses LUT fitting L2", lut)
        return self._non_lut_selection("PackedBatchGF2Kernel", "default vectorized fallback")

    def _best_lut_candidate(self) -> dict[str, Any]:
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
        for cache_key in ("fits_l2", "fits_l3"):
            fitting = [estimate for estimate in estimates if estimate[cache_key]]
            if fitting:
                return max(fitting, key=lambda estimate: int(estimate["block_width"]))
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
            selection_reason=reason,
        )

    def _non_lut_selection(self, backend: str, reason: str) -> CacheAwareSelection:
        return CacheAwareSelection(
            selected_backend=backend,
            selected_block_width=0,
            lut_bytes=0,
            fits_l1=True,
            fits_l2=True,
            fits_l3=True,
            selection_reason=reason,
        )
