"""Cache-aware block-LUT backend."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_batch, require_gf2_matrix, require_gf2_vector


class BlockLUTKernel:
    """Backend using block-wise lookup tables for fixed GF(2) kernels.

    Block-LUT is treated as one backend primitive, not as a standalone coding
    contribution.
    """

    def __init__(self, matrix: np.ndarray, block_width: int) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.block_width = int(block_width)
        if self.block_width <= 0:
            raise ValueError("block_width must be positive")
        self.n, self.r = self.matrix.shape
        self.blocks = self._build_blocks()

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the block-LUT backend."""
        x = require_gf2_vector(x, self.n)
        y = np.zeros(self.r, dtype=np.uint8)
        for start, end, bit_weights, table in self.blocks:
            local_bits = x[start:end]
            mask = int(local_bits @ bit_weights)
            y ^= table[mask]
        return y

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the block-LUT backend to a batch."""
        x_batch = require_gf2_batch(x_batch, self.n)
        return np.stack([self.apply(x) for x in x_batch]).astype(np.uint8)

    def _build_blocks(self) -> list[tuple[int, int, np.ndarray, np.ndarray]]:
        blocks = []
        for start in range(0, self.n, self.block_width):
            end = min(start + self.block_width, self.n)
            block_matrix = self.matrix[start:end]
            width = end - start
            bit_weights = (1 << np.arange(width, dtype=np.uint64)).astype(np.uint64)
            table = self._build_table(block_matrix)
            blocks.append((start, end, bit_weights, table))
        return blocks

    @staticmethod
    def _build_table(block_matrix: np.ndarray) -> np.ndarray:
        width, output_width = block_matrix.shape
        table = np.zeros((1 << width, output_width), dtype=np.uint8)
        for bit_index in range(width):
            bit = 1 << bit_index
            previous = table[:bit].copy()
            table[bit : 2 * bit] = previous ^ block_matrix[bit_index]
        return table
