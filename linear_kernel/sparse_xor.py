"""Sparse-column XOR backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_matrix


class SparseXorKernel:
    """Backend for sparse inputs using XOR over active columns/rows."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the sparse XOR backend."""
        raise NotImplementedError("SparseXorKernel.apply will be implemented later")
