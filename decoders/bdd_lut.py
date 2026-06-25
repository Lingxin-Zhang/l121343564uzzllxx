"""Bounded-distance decoder LUT for small GF(2) component syndromes."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np

from linear_kernel.matrix_utils import (
    pack_batch_bits_to_uint16,
    pack_batch_bits_to_uint32,
    pack_bits_to_uint16,
    pack_bits_to_uint32,
    require_gf2_batch,
    require_gf2_matrix,
    require_gf2_vector,
)
from linear_kernel.naive import NaiveGF2Kernel

STATUS_NO_ERROR = "no_error"
STATUS_CORRECTED = "corrected"
STATUS_FAILURE = "failure"


@dataclass(frozen=True)
class DecodeResult:
    """Single component decode result."""

    correction_mask: np.ndarray
    corrected_word: np.ndarray | None
    status: str
    correction_weight: int
    syndrome_packed: int


class BDDLUTDecoder:
    """Syndrome lookup table for t<=2 bounded-distance correction.

    The input matrix has shape ``(n, r)`` and maps an error mask ``e`` to a
    syndrome ``e @ matrix mod 2``. The LUT stores all syndromes reachable by
    zero, one, or two bit flips. Unknown syndromes return ``failure`` with an
    all-zero correction mask.
    """

    def __init__(
        self,
        matrix: np.ndarray,
        *,
        t: int = 2,
        strict_collision_check: bool = True,
    ) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape
        self.t = int(t)
        if self.t < 0 or self.t > 2:
            raise ValueError("BDDLUTDecoder currently supports t in [0, 2]")
        if self.r < 1 or self.r > 32:
            raise ValueError("BDDLUTDecoder currently supports syndrome width r in [1, 32]")
        self.strict_collision_check = bool(strict_collision_check)
        self.collision_count = 0
        self._lut: dict[int, tuple[tuple[int, ...], str]] = {}
        self._row_keys = np.array([self._pack_bits(row) for row in self.matrix], dtype=np.uint64)
        self._build_lut()

    def _pack_bits(self, bits: np.ndarray) -> int:
        if self.r <= 16:
            return int(pack_bits_to_uint16(bits))
        return int(pack_bits_to_uint32(bits))

    def _pack_batch(self, bits: np.ndarray) -> np.ndarray:
        if self.r <= 16:
            return pack_batch_bits_to_uint16(bits)
        return pack_batch_bits_to_uint32(bits)

    def _build_lut(self) -> None:
        self._add_entry(0, (), STATUS_NO_ERROR)
        if self.t >= 1:
            for i in range(self.n):
                self._add_entry(int(self._row_keys[i]), (i,), STATUS_CORRECTED)
        if self.t >= 2:
            for i, j in combinations(range(self.n), 2):
                self._add_entry(
                    int(self._row_keys[i] ^ self._row_keys[j]),
                    (i, j),
                    STATUS_CORRECTED,
                )

    def _add_entry(self, key: int, positions: tuple[int, ...], status: str) -> None:
        existing = self._lut.get(key)
        if existing is None:
            self._lut[key] = (positions, status)
            return
        if existing == (positions, status):
            return
        self.collision_count += 1
        if self.strict_collision_check:
            raise ValueError(
                "BDD LUT collision detected for packed syndrome "
                f"{key}: existing={existing[0]}, new={positions}"
            )

    def _mask_from_positions(self, positions: tuple[int, ...]) -> np.ndarray:
        mask = np.zeros(self.n, dtype=np.uint8)
        if positions:
            mask[np.array(positions, dtype=np.int64)] = 1
        return mask

    def decode_packed_syndrome(self, syndrome_packed: int | np.integer[Any]) -> DecodeResult:
        """Decode one already-packed syndrome integer."""
        key = int(syndrome_packed)
        positions, status = self._lut.get(key, ((), STATUS_FAILURE))
        mask = self._mask_from_positions(positions)
        return DecodeResult(
            correction_mask=mask,
            corrected_word=None,
            status=status,
            correction_weight=len(positions) if status != STATUS_FAILURE else 0,
            syndrome_packed=key,
        )

    def decode_syndrome(self, syndrome: np.ndarray) -> DecodeResult:
        """Decode one unpacked syndrome vector of shape ``(r,)``."""
        syndrome = require_gf2_vector(syndrome, self.r)
        return self.decode_packed_syndrome(self._pack_bits(syndrome))

    def decode(self, syndrome: np.ndarray) -> DecodeResult:
        """Backward-compatible alias for ``decode_syndrome``."""
        return self.decode_syndrome(syndrome)

    def decode_syndromes(self, syndromes: np.ndarray) -> dict[str, np.ndarray]:
        """Decode a batch of unpacked syndromes or packed syndrome integers."""
        packed = self._normalize_syndrome_batch(syndromes)
        results = [self.decode_packed_syndrome(value) for value in packed]
        return self._batch_from_results(results)

    def decode_word(self, y: np.ndarray, syndrome_backend: object | None = None) -> DecodeResult:
        """Decode one received word using the supplied syndrome backend."""
        y = require_gf2_vector(y, self.n)
        result = self._decode_word_result(y, syndrome_backend)
        return result

    def decode_words(
        self,
        y_batch: np.ndarray,
        syndrome_backend: object | None = None,
    ) -> dict[str, np.ndarray]:
        """Decode a batch of received words using one syndrome backend."""
        y_batch = require_gf2_batch(y_batch, self.n)
        packed = self._compute_packed_syndromes(y_batch, syndrome_backend)
        results = [self.decode_packed_syndrome(value) for value in packed]
        out = self._batch_from_results(results)
        corrected = y_batch.copy()
        non_failure = out["statuses"] != STATUS_FAILURE
        corrected[non_failure] ^= out["correction_masks"][non_failure]
        out["corrected_words"] = corrected.astype(np.uint8, copy=False)
        return out

    def _decode_word_result(
        self,
        y: np.ndarray,
        syndrome_backend: object | None,
    ) -> DecodeResult:
        packed = self._compute_packed_syndromes(y.reshape(1, -1), syndrome_backend)[0]
        result = self.decode_packed_syndrome(packed)
        corrected = y.copy()
        if result.status != STATUS_FAILURE:
            corrected ^= result.correction_mask
        return DecodeResult(
            correction_mask=result.correction_mask,
            corrected_word=corrected.astype(np.uint8, copy=False),
            status=result.status,
            correction_weight=result.correction_weight,
            syndrome_packed=result.syndrome_packed,
        )

    def _compute_packed_syndromes(
        self,
        y_batch: np.ndarray,
        syndrome_backend: object | None,
    ) -> np.ndarray:
        if syndrome_backend is None:
            syndromes = NaiveGF2Kernel(self.matrix).apply_many(y_batch)
            return self._pack_batch(syndromes)
        if hasattr(syndrome_backend, "apply_many_packed"):
            return np.asarray(syndrome_backend.apply_many_packed(y_batch))
        if hasattr(syndrome_backend, "apply_many"):
            syndromes = syndrome_backend.apply_many(y_batch)
            return self._pack_batch(require_gf2_batch(syndromes, self.r))
        raise TypeError("syndrome_backend must provide apply_many or apply_many_packed")

    def _normalize_syndrome_batch(self, syndromes: np.ndarray) -> np.ndarray:
        syndromes = np.asarray(syndromes)
        if syndromes.ndim == 2:
            return self._pack_batch(require_gf2_batch(syndromes, self.r))
        if syndromes.ndim == 1 and np.issubdtype(syndromes.dtype, np.integer):
            if syndromes.dtype == np.uint8:
                raise ValueError("unpacked syndrome batches must be 2-D")
            return syndromes
        raise ValueError("syndromes must be a 2-D unpacked batch or a 1-D packed integer array")

    def _batch_from_results(self, results: list[DecodeResult]) -> dict[str, np.ndarray]:
        masks = (
            np.stack([result.correction_mask for result in results], axis=0)
            if results
            else np.zeros((0, self.n), dtype=np.uint8)
        )
        statuses = np.array([result.status for result in results], dtype=object)
        weights = np.array([result.correction_weight for result in results], dtype=np.uint8)
        packed = np.array(
            [result.syndrome_packed for result in results],
            dtype=np.uint16 if self.r <= 16 else np.uint32,
        )
        return {
            "correction_masks": masks,
            "statuses": statuses,
            "correction_weights": weights,
            "syndrome_packed": packed,
        }
