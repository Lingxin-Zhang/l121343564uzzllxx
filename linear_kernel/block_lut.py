"""Cache-aware block-LUT backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_matrix


class BlockLUTKernel:
    """Backend using block-wise lookup tables for fixed GF(2) kernels.

    Block-LUT is treated as one backend primitive, not as a standalone coding
    contribution.
    """

    def __init__(self, matrix: np.ndarray, block_width: int) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.block_width = int(block_width)

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the block-LUT backend."""
        raise NotImplementedError("BlockLUTKernel.apply will be implemented later")
