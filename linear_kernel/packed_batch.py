"""Packed batch GF(2) backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_batch, require_gf2_matrix


class PackedBatchGF2Kernel:
    """Correctness-first batch backend.

    This implementation keeps unpacked inputs/outputs and uses NumPy matrix
    multiplication modulo 2. True packed-bit optimization is intentionally
    deferred.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the batch backend to unpacked GF(2) inputs."""
        x_batch = require_gf2_batch(x_batch, self.n)
        return ((x_batch.astype(np.int64) @ self.matrix.astype(np.int64)) & 1).astype(np.uint8)
