"""Correctness tests for BCH-like component syndrome kernels."""

from __future__ import annotations

import numpy as np

from codes.bch_like import (
    BCH255_T2_SYNDROME_SPEC,
    make_bch255_t2_syndrome_matrix,
)
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16


def assert_unpacked_bits(array: np.ndarray, expected_shape: tuple[int, ...]) -> None:
    assert array.shape == expected_shape
    assert array.dtype == np.uint8
    assert np.all((array == 0) | (array == 1))


def test_bch255_t2_syndrome_matrix_shape_dtype_and_bits() -> None:
    matrix = make_bch255_t2_syndrome_matrix()

    assert matrix.shape == (255, 16)
    assert matrix.dtype == np.uint8
    assert np.all((matrix == 0) | (matrix == 1))
    assert BCH255_T2_SYNDROME_SPEC.n == 255
    assert BCH255_T2_SYNDROME_SPEC.r == 16


def test_bch255_t2_syndrome_matrix_is_deterministic() -> None:
    first = make_bch255_t2_syndrome_matrix()
    second = make_bch255_t2_syndrome_matrix()

    np.testing.assert_array_equal(first, second)


def test_bch255_t2_zero_word_has_zero_syndrome() -> None:
    matrix = make_bch255_t2_syndrome_matrix()
    kernel = NaiveGF2Kernel(matrix)

    syndrome = kernel.apply(np.zeros(255, dtype=np.uint8))

    assert_unpacked_bits(syndrome, (16,))
    np.testing.assert_array_equal(syndrome, np.zeros(16, dtype=np.uint8))


def test_bch255_t2_syndrome_backends_match_for_random_words() -> None:
    matrix = make_bch255_t2_syndrome_matrix()
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_block = PackedBlockLUTKernel(matrix, block_width=8)

    for batch_size in (1, 64, 4096):
        for density in (0.005, 0.05, 0.5):
            rng = np.random.default_rng(20260704 + batch_size)
            received = (rng.random((batch_size, 255)) < density).astype(np.uint8)
            expected = naive.apply_many(received)
            expected_packed = pack_batch_bits_to_uint16(expected)

            actual_packed_batch = packed_batch.apply_many(received)
            actual_packed_block = packed_block.apply_many(received)
            actual_packed_block_packed = packed_block.apply_many_packed(received)

            assert_unpacked_bits(expected, (batch_size, 16))
            np.testing.assert_array_equal(actual_packed_batch, expected)
            np.testing.assert_array_equal(actual_packed_block, expected)
            np.testing.assert_array_equal(actual_packed_block_packed, expected_packed)
