"""Correctness tests for bit-exact GF(2) backends."""

from __future__ import annotations

import numpy as np
import pytest

from linear_kernel import BlockLUTKernel, NaiveGF2Kernel, SparseXorKernel


def test_package_imports() -> None:
    from linear_kernel import (  # noqa: F401
        BlockLUTKernel,
        EventUpdateKernel,
        HybridPlanner,
        NaiveGF2Kernel,
        PackedBatchGF2Kernel,
        SparseXorKernel,
    )


def oracle_gf2_apply_many(x_batch: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Independent GF(2) oracle for tests."""
    return ((x_batch.astype(np.int64) @ matrix.astype(np.int64)) & 1).astype(np.uint8)


@pytest.fixture(scope="module")
def random_matrix() -> np.ndarray:
    rng = np.random.default_rng(20260624)
    return rng.integers(0, 2, size=(255, 16), dtype=np.uint8)


@pytest.fixture(scope="module")
def density_batches() -> dict[float, np.ndarray]:
    rng = np.random.default_rng(20260625)
    return {
        density: (rng.random((1000, 255)) < density).astype(np.uint8)
        for density in (0.01, 0.05, 0.5)
    }


def assert_unpacked_bits(array: np.ndarray, expected_shape: tuple[int, ...]) -> None:
    assert array.shape == expected_shape
    assert array.dtype == np.uint8
    assert np.all((array == 0) | (array == 1))


@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_naive_apply_and_apply_many_match_oracle(
    random_matrix: np.ndarray,
    density_batches: dict[float, np.ndarray],
    density: float,
) -> None:
    kernel = NaiveGF2Kernel(random_matrix)
    x_batch = density_batches[density]
    expected_batch = oracle_gf2_apply_many(x_batch, random_matrix)

    actual_batch = kernel.apply_many(x_batch)

    assert_unpacked_bits(actual_batch, (1000, 16))
    np.testing.assert_array_equal(actual_batch, expected_batch)

    for x, expected in zip(x_batch, expected_batch, strict=True):
        actual = kernel.apply(x)
        assert_unpacked_bits(actual, (16,))
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("kernel_factory", [NaiveGF2Kernel, SparseXorKernel])
def test_apply_rejects_wrong_vector_length(
    random_matrix: np.ndarray,
    kernel_factory: type[NaiveGF2Kernel] | type[SparseXorKernel],
) -> None:
    kernel = kernel_factory(random_matrix)

    with pytest.raises(ValueError, match="does not match matrix n=255"):
        kernel.apply(np.zeros(254, dtype=np.uint8))


@pytest.mark.parametrize("kernel_factory", [NaiveGF2Kernel, SparseXorKernel])
def test_apply_many_rejects_wrong_batch_width(
    random_matrix: np.ndarray,
    kernel_factory: type[NaiveGF2Kernel] | type[SparseXorKernel],
) -> None:
    kernel = kernel_factory(random_matrix)

    with pytest.raises(ValueError, match="does not match matrix n=255"):
        kernel.apply_many(np.zeros((4, 254), dtype=np.uint8))


def test_block_lut_rejects_wrong_input_width(random_matrix: np.ndarray) -> None:
    kernel = BlockLUTKernel(random_matrix, block_width=8)

    with pytest.raises(ValueError, match="does not match matrix n=255"):
        kernel.apply(np.zeros(254, dtype=np.uint8))

    with pytest.raises(ValueError, match="does not match matrix n=255"):
        kernel.apply_many(np.zeros((4, 254), dtype=np.uint8))


@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_sparse_apply_and_apply_many_match_naive(
    random_matrix: np.ndarray,
    density_batches: dict[float, np.ndarray],
    density: float,
) -> None:
    naive = NaiveGF2Kernel(random_matrix)
    sparse = SparseXorKernel(random_matrix)
    x_batch = density_batches[density]
    expected_batch = naive.apply_many(x_batch)

    actual_batch = sparse.apply_many(x_batch)

    assert_unpacked_bits(actual_batch, (1000, 16))
    np.testing.assert_array_equal(actual_batch, expected_batch)

    for x, expected in zip(x_batch, expected_batch, strict=True):
        actual = sparse.apply(x)
        assert_unpacked_bits(actual, (16,))
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("block_width", [4, 8, 12, 16, 20])
@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_block_lut_apply_and_apply_many_match_naive(
    random_matrix: np.ndarray,
    density_batches: dict[float, np.ndarray],
    density: float,
    block_width: int,
) -> None:
    naive = NaiveGF2Kernel(random_matrix)
    block_lut = BlockLUTKernel(random_matrix, block_width=block_width)
    x_batch = density_batches[density]
    expected_batch = naive.apply_many(x_batch)

    actual_batch = block_lut.apply_many(x_batch)

    assert_unpacked_bits(actual_batch, (1000, 16))
    np.testing.assert_array_equal(actual_batch, expected_batch)

    for x, expected in zip(x_batch, expected_batch, strict=True):
        actual = block_lut.apply(x)
        assert_unpacked_bits(actual, (16,))
        np.testing.assert_array_equal(actual, expected)
