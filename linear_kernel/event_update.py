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

    def update_many(
        self,
        current_values: np.ndarray,
        flipped_positions: np.ndarray,
    ) -> np.ndarray:
        """Update a batch of existing outputs after per-row bit flip events."""
        new_values = self._require_current_values(current_values)
        positions = self._require_position_batch(flipped_positions, new_values.shape[0])
        if positions.shape[1] == 0:
            return new_values
        contributions = np.bitwise_xor.reduce(self.matrix[positions], axis=1).astype(
            np.uint8,
            copy=False,
        )
        return new_values ^ contributions

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

    def _require_current_values(self, current_values: np.ndarray) -> np.ndarray:
        values = as_gf2_array(current_values)
        if values.ndim != 2:
            raise ValueError("current_values must be 2-D")
        if values.shape[1] != self.r:
            raise ValueError(
                f"current_values width {values.shape[1]} does not match matrix r={self.r}"
            )
        return values.copy()

    def _require_position_batch(
        self,
        flipped_positions: np.ndarray,
        batch_size: int,
    ) -> np.ndarray:
        positions = np.asarray(flipped_positions)
        if positions.ndim != 2:
            raise ValueError("flipped_positions must be 2-D")
        if positions.shape[0] != batch_size:
            raise ValueError(
                "flipped_positions batch size "
                f"{positions.shape[0]} does not match current_values batch size {batch_size}"
            )
        if not np.issubdtype(positions.dtype, np.integer):
            raise ValueError("flipped_positions must contain integer positions")
        positions = positions.astype(np.int64, copy=False)
        if positions.size and np.any((positions < 0) | (positions >= self.n)):
            raise ValueError(f"flipped_positions must be in [0, {self.n})")
        return positions
