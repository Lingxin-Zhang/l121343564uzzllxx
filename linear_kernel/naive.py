"""Baseline GF(2) matrix-vector and matrix-batch execution."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_matrix


class NaiveGF2Kernel:
    """Reference backend for f(x) = xA over GF(2).

    This backend is the correctness oracle for all optimized backends. Full
    implementation is intentionally deferred until the next development round.
    """

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the kernel to one vector or a batch of vectors."""
        raise NotImplementedError("NaiveGF2Kernel.apply will be implemented later")
