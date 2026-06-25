"""Packed uint16 block-LUT backend."""

from __future__ import annotations

import numpy as np

from .matrix_utils import (
    pack_bits_to_uint16,
    require_gf2_batch,
    require_gf2_matrix,
    require_gf2_vector,
    unpack_uint16_to_bits,
)


class PackedBlockLUTKernel:
    """Block-LUT backend whose table entries are packed ``np.uint16`` values."""

    def __init__(self, matrix: np.ndarray, block_width: int) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.block_width = int(block_width)
        if self.block_width <= 0:
            raise ValueError("block_width must be positive")
        self.n, self.r = self.matrix.shape
        if self.r > 16:
            raise ValueError("PackedBlockLUT output width must be at most 16")
        self.blocks = self._build_blocks()

    def apply_packed(self, x: np.ndarray) -> np.uint16:
        """Apply the backend to one unpacked input and return packed output."""
        x = require_gf2_vector(x, self.n)
        acc = np.uint16(0)
        for start, end, bit_weights, table in self.blocks:
            local_bits = x[start:end]
            mask = int(local_bits @ bit_weights)
            acc ^= table[mask]
        return np.uint16(acc)

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the backend and return an unpacked GF(2) output vector."""
        return unpack_uint16_to_bits(self.apply_packed(x), self.r)

    def apply_many_packed(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the backend to a batch and return packed uint16 outputs."""
        x_batch = require_gf2_batch(x_batch, self.n)
        acc = np.zeros(x_batch.shape[0], dtype=np.uint16)
        for start, end, bit_weights, table in self.blocks:
            local_bits = x_batch[:, start:end]
            masks = (local_bits @ bit_weights).astype(np.intp, copy=False)
            acc ^= table[masks]
        return acc

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the backend and return an unpacked GF(2) output matrix."""
        packed = self.apply_many_packed(x_batch)
        shifts = np.arange(self.r, dtype=np.uint16)
        return ((packed[:, None] >> shifts) & np.uint16(1)).astype(np.uint8)

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
        width, _ = block_matrix.shape
        table = np.zeros(1 << width, dtype=np.uint16)
        for bit_index in range(width):
            bit = 1 << bit_index
            previous = table[:bit].copy()
            contribution = pack_bits_to_uint16(block_matrix[bit_index])
            table[bit : 2 * bit] = previous ^ contribution
        return table
