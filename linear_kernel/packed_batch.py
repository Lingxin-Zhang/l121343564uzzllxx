"""Packed batch GF(2) backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_matrix


class PackedBatchGF2Kernel:
    """Backend for batch workloads using packed bit operations."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the packed backend to a batch."""
        raise NotImplementedError("PackedBatchGF2Kernel.apply_many will be implemented later")
