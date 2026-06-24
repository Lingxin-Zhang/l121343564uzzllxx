"""Baseline GF(2) matrix-vector and matrix-batch execution."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_batch, require_gf2_matrix, require_gf2_vector


class NaiveGF2Kernel:
    """Reference backend for f(x) = xA over GF(2).

    This backend is the correctness oracle for all optimized backends.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the kernel to one unpacked input vector."""
        x = require_gf2_vector(x, self.n)
        return ((x.astype(np.int64) @ self.matrix.astype(np.int64)) & 1).astype(np.uint8)

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the kernel to an unpacked batch of input vectors."""
        x_batch = require_gf2_batch(x_batch, self.n)
        return ((x_batch.astype(np.int64) @ self.matrix.astype(np.int64)) & 1).astype(np.uint8)
