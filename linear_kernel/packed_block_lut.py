"""Packed uint16/uint32 block-LUT backend."""

from __future__ import annotations

import numpy as np

from .matrix_utils import (
    pack_bits_to_uint32,
    pack_bits_to_uint16,
    require_gf2_batch,
    require_gf2_matrix,
    require_gf2_vector,
    unpack_uint32_to_bits,
    unpack_uint16_to_bits,
)


class PackedBlockLUTKernel:
    """Block-LUT backend whose table entries are packed integer values."""

    def __init__(
        self,
        matrix: np.ndarray,
        block_width: int,
        packed_word_bits: int | None = None,
    ) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.block_width = int(block_width)
        if self.block_width <= 0:
            raise ValueError("block_width must be positive")
        self.n, self.r = self.matrix.shape
        self.packed_word_bits = self._resolve_packed_word_bits(packed_word_bits)
        self.packed_dtype = np.uint16 if self.packed_word_bits == 16 else np.uint32
        self.blocks = self._build_blocks()

    def apply_packed(self, x: np.ndarray) -> np.uint16 | np.uint32:
        """Apply the backend to one unpacked input and return packed output."""
        x = require_gf2_vector(x, self.n)
        acc = self.packed_dtype(0)
        for start, end, bit_weights, table in self.blocks:
            local_bits = x[start:end]
            mask = int(local_bits @ bit_weights)
            acc ^= table[mask]
        return self.packed_dtype(acc)

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Apply the backend and return an unpacked GF(2) output vector."""
        return self._unpack_value(self.apply_packed(x))

    def apply_many_packed(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the backend to a batch and return packed integer outputs."""
        x_batch = require_gf2_batch(x_batch, self.n)
        acc = np.zeros(x_batch.shape[0], dtype=self.packed_dtype)
        for start, end, bit_weights, table in self.blocks:
            local_bits = x_batch[:, start:end]
            masks = (local_bits @ bit_weights).astype(np.intp, copy=False)
            acc ^= table[masks]
        return acc

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Apply the backend and return an unpacked GF(2) output matrix."""
        packed = self.apply_many_packed(x_batch)
        shift_dtype = np.uint16 if self.packed_word_bits == 16 else np.uint32
        shifts = np.arange(self.r, dtype=shift_dtype)
        return ((packed[:, None] >> shifts) & shift_dtype(1)).astype(np.uint8)

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

    def _resolve_packed_word_bits(self, packed_word_bits: int | None) -> int:
        if packed_word_bits is None:
            packed_word_bits = 16 if self.r <= 16 else 32
        packed_word_bits = int(packed_word_bits)
        if packed_word_bits not in (16, 32):
            raise ValueError("packed_word_bits must be 16 or 32")
        if self.r > packed_word_bits:
            raise ValueError(
                f"PackedBlockLUT output width must be at most {packed_word_bits}"
            )
        if self.r > 32:
            raise ValueError("PackedBlockLUT output width must be at most 32")
        return packed_word_bits

    def _pack_bits(self, bits: np.ndarray) -> np.uint16 | np.uint32:
        if self.packed_word_bits == 16:
            return pack_bits_to_uint16(bits)
        return pack_bits_to_uint32(bits)

    def _unpack_value(self, value: np.uint16 | np.uint32) -> np.ndarray:
        if self.packed_word_bits == 16:
            return unpack_uint16_to_bits(value, self.r)
        return unpack_uint32_to_bits(value, self.r)

    def _build_table(self, block_matrix: np.ndarray) -> np.ndarray:
        width, _ = block_matrix.shape
        table = np.zeros(1 << width, dtype=self.packed_dtype)
        for bit_index in range(width):
            bit = 1 << bit_index
            previous = table[:bit].copy()
            contribution = self._pack_bits(block_matrix[bit_index])
            table[bit : 2 * bit] = previous ^ contribution
        return table
