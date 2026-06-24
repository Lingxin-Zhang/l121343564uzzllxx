"""Event-driven syndrome update backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import as_gf2_array, require_gf2_matrix


class EventUpdateKernel:
    """Backend for updating f(x) after a small number of bit flips."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape

    def update(self, current_value: np.ndarray, flipped_positions: np.ndarray) -> np.ndarray:
        """Update an existing output after bit flip events."""
        new_value = self._require_current_value(current_value)
        positions = self._require_positions(flipped_positions)
        if positions.size == 0:
            return new_value
        new_value ^= np.bitwise_xor.reduce(self.matrix[positions], axis=0).astype(np.uint8)
        return new_value

    def _require_current_value(self, current_value: np.ndarray) -> np.ndarray:
        value = as_gf2_array(current_value)
        if value.ndim != 1:
            raise ValueError("current_value must be 1-D")
        if value.shape[0] != self.r:
            raise ValueError(
                f"current_value length {value.shape[0]} does not match matrix r={self.r}"
            )
        return value.copy()

    def _require_positions(self, flipped_positions: np.ndarray) -> np.ndarray:
        positions = np.asarray(flipped_positions)
        if positions.ndim != 1:
            raise ValueError("flipped_positions must be 1-D")
        if not np.issubdtype(positions.dtype, np.integer):
            raise ValueError("flipped_positions must contain integer positions")
        positions = positions.astype(np.int64, copy=False)
        if np.any((positions < 0) | (positions >= self.n)):
            raise ValueError(f"flipped_positions must be in [0, {self.n})")
        return positions
