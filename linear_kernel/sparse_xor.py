"""Sparse-position XOR backend."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_batch, require_gf2_matrix, require_gf2_vector


class SparseXorKernel:
    """Backend for sparse inputs using XOR over active position contributions."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape
        self.position_contribution = self.matrix.copy()

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the sparse XOR backend."""
        x = require_gf2_vector(x, self.n)
        active_positions = np.flatnonzero(x)
        if active_positions.size == 0:
            return np.zeros(self.r, dtype=np.uint8)
        return np.bitwise_xor.reduce(
            self.position_contribution[active_positions], axis=0
        ).astype(np.uint8)

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the sparse XOR backend to a batch."""
        x_batch = require_gf2_batch(x_batch, self.n)
        return np.stack([self.apply(x) for x in x_batch]).astype(np.uint8)
