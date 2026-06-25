"""Tests for packed uint32 output support."""

from __future__ import annotations

import numpy as np
import pytest

from linear_kernel import NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import (
    pack_batch_bits_to_uint32,
    pack_bits_to_uint32,
    unpack_uint32_to_bits,
)


@pytest.mark.parametrize("width", [17, 31, 32])
def test_pack_bits_to_uint32_roundtrip(width: int) -> None:
    rng = np.random.default_rng(20260710 + width)
    bits = rng.integers(0, 2, size=width, dtype=np.uint8)

    packed = pack_bits_to_uint32(bits)
    unpacked = unpack_uint32_to_bits(packed, width)

    assert isinstance(packed, np.uint32)
    assert unpacked.dtype == np.uint8
    np.testing.assert_array_equal(unpacked, bits)


def test_pack_batch_bits_to_uint32_roundtrip() -> None:
    rng = np.random.default_rng(20260711)
    bits = rng.integers(0, 2, size=(5, 32), dtype=np.uint8)

    packed = pack_batch_bits_to_uint32(bits)
    unpacked = np.stack([unpack_uint32_to_bits(value, 32) for value in packed])

    assert packed.shape == (5,)
    assert packed.dtype == np.uint32
    np.testing.assert_array_equal(unpacked, bits)


@pytest.mark.parametrize("width", [0, 33])
def test_uint32_pack_rejects_invalid_width(width: int) -> None:
    with pytest.raises(ValueError, match="uint32 packing width"):
        pack_bits_to_uint32(np.ones(width, dtype=np.uint8))


@pytest.mark.parametrize("r", [17, 32])
@pytest.mark.parametrize("block_width", [4, 8, 12])
def test_packed_block_lut_r32_matches_naive(r: int, block_width: int) -> None:
    rng = np.random.default_rng(20260712 + r + block_width)
    matrix = rng.integers(0, 2, size=(63, r), dtype=np.uint8)
    x_batch = rng.integers(0, 2, size=(128, 63), dtype=np.uint8)
    naive = NaiveGF2Kernel(matrix)
    packed = PackedBlockLUTKernel(matrix, block_width=block_width)

    expected = naive.apply_many(x_batch)
    actual = packed.apply_many(x_batch)
    actual_packed = packed.apply_many_packed(x_batch)
    expected_packed = pack_batch_bits_to_uint32(expected)

    assert actual.dtype == np.uint8
    assert actual.shape == (128, r)
    assert actual_packed.dtype == np.uint32
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(actual_packed, expected_packed)


def test_packed_block_lut_rejects_output_width_over_32() -> None:
    matrix = np.zeros((8, 33), dtype=np.uint8)

    with pytest.raises(ValueError, match="at most 32"):
        PackedBlockLUTKernel(matrix, block_width=4)
