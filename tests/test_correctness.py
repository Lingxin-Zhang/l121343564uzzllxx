"""Correctness tests for bit-exact GF(2) backends."""

from __future__ import annotations

import numpy as np
import pytest

from linear_kernel import (
    BlockLUTKernel,
    EventUpdateKernel,
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    PackedBlockLUTKernel,
    SparseXorKernel,
)
from linear_kernel.matrix_utils import (
    pack_batch_bits_to_uint16,
    pack_bits_to_uint16,
    unpack_uint16_to_bits,
)


def test_package_imports() -> None:
    from linear_kernel import (  # noqa: F401
        BlockLUTKernel,
        EventUpdateKernel,
        HybridPlanner,
        NaiveGF2Kernel,
        PackedBatchGF2Kernel,
        PackedBlockLUTKernel,
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


def test_pack_bits_to_uint16_roundtrip() -> None:
    bits = np.array([1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0], dtype=np.uint8)

    packed = pack_bits_to_uint16(bits)
    unpacked = unpack_uint16_to_bits(packed, width=16)

    assert isinstance(packed, np.uint16)
    assert_unpacked_bits(unpacked, (16,))
    np.testing.assert_array_equal(unpacked, bits)
    assert int(packed) == sum(int(bit) << idx for idx, bit in enumerate(bits))


def test_pack_bits_to_uint16_rejects_invalid_width() -> None:
    with pytest.raises(ValueError, match="at most 16"):
        pack_bits_to_uint16(np.ones(17, dtype=np.uint8))

    with pytest.raises(ValueError, match="width must be in"):
        unpack_uint16_to_bits(np.uint16(0), width=17)


def test_pack_bits_to_uint16_rejects_non_vector() -> None:
    with pytest.raises(ValueError, match="must be 1-D"):
        pack_bits_to_uint16(np.ones((1, 4), dtype=np.uint8))


def test_pack_batch_bits_to_uint16_roundtrip() -> None:
    batch = np.array(
        [
            [1, 0, 1, 1],
            [0, 1, 0, 1],
            [1, 1, 1, 1],
        ],
        dtype=np.uint8,
    )

    packed = pack_batch_bits_to_uint16(batch)
    unpacked = np.stack([unpack_uint16_to_bits(value, width=4) for value in packed])

    assert packed.shape == (3,)
    assert packed.dtype == np.uint16
    assert_unpacked_bits(unpacked, batch.shape)
    np.testing.assert_array_equal(unpacked, batch)


def test_pack_batch_bits_to_uint16_rejects_invalid_shape() -> None:
    with pytest.raises(ValueError, match="must be 2-D"):
        pack_batch_bits_to_uint16(np.ones(4, dtype=np.uint8))

    with pytest.raises(ValueError, match="at most 16"):
        pack_batch_bits_to_uint16(np.ones((2, 17), dtype=np.uint8))


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


@pytest.mark.parametrize("block_width", [4, 8, 12, 16, 20])
@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_packed_block_lut_apply_and_apply_many_match_naive(
    random_matrix: np.ndarray,
    density_batches: dict[float, np.ndarray],
    density: float,
    block_width: int,
) -> None:
    naive = NaiveGF2Kernel(random_matrix)
    packed_block_lut = PackedBlockLUTKernel(random_matrix, block_width=block_width)
    x_batch = density_batches[density]
    expected_batch = naive.apply_many(x_batch)

    actual_batch = packed_block_lut.apply_many(x_batch)

    assert_unpacked_bits(actual_batch, (1000, 16))
    np.testing.assert_array_equal(actual_batch, expected_batch)

    for x, expected in zip(x_batch, expected_batch, strict=True):
        actual = packed_block_lut.apply(x)
        assert_unpacked_bits(actual, (16,))
        np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("block_width", [4, 8, 12, 16, 20])
@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_packed_block_lut_apply_packed_matches_packed_naive(
    random_matrix: np.ndarray,
    density_batches: dict[float, np.ndarray],
    density: float,
    block_width: int,
) -> None:
    naive = NaiveGF2Kernel(random_matrix)
    packed_block_lut = PackedBlockLUTKernel(random_matrix, block_width=block_width)
    x_batch = density_batches[density]
    expected_batch = naive.apply_many(x_batch)

    actual_packed = packed_block_lut.apply_many_packed(x_batch)
    expected_packed = pack_batch_bits_to_uint16(expected_batch)

    assert actual_packed.shape == (1000,)
    assert actual_packed.dtype == np.uint16
    np.testing.assert_array_equal(actual_packed, expected_packed)

    for x, expected in zip(x_batch, expected_packed, strict=True):
        actual = packed_block_lut.apply_packed(x)
        assert isinstance(actual, np.uint16)
        assert actual == expected


def test_packed_block_lut_rejects_output_width_over_16() -> None:
    matrix = np.zeros((4, 17), dtype=np.uint8)

    with pytest.raises(ValueError, match="output width"):
        PackedBlockLUTKernel(matrix, block_width=4)


@pytest.mark.parametrize("flip_count", [1, 2, 5, 10])
def test_event_update_matches_naive_recompute(
    random_matrix: np.ndarray,
    flip_count: int,
) -> None:
    rng = np.random.default_rng(20260626 + flip_count)
    x = rng.integers(0, 2, size=255, dtype=np.uint8)
    flipped_positions = rng.choice(255, size=flip_count, replace=False)
    x_flipped = x.copy()
    x_flipped[flipped_positions] ^= 1

    naive = NaiveGF2Kernel(random_matrix)
    event_update = EventUpdateKernel(random_matrix)
    old = naive.apply(x)
    old_before_update = old.copy()
    expected = naive.apply(x_flipped)

    actual = event_update.update(old, flipped_positions)

    assert_unpacked_bits(actual, (16,))
    np.testing.assert_array_equal(actual, expected)
    np.testing.assert_array_equal(old, old_before_update)


def test_event_update_accepts_list_positions(random_matrix: np.ndarray) -> None:
    x = np.zeros(255, dtype=np.uint8)
    flipped_positions = [0, 7, 254]
    x_flipped = x.copy()
    x_flipped[flipped_positions] ^= 1

    naive = NaiveGF2Kernel(random_matrix)
    event_update = EventUpdateKernel(random_matrix)

    actual = event_update.update(naive.apply(x), flipped_positions)
    expected = naive.apply(x_flipped)

    assert_unpacked_bits(actual, (16,))
    np.testing.assert_array_equal(actual, expected)


def test_event_update_rejects_wrong_current_value_length(random_matrix: np.ndarray) -> None:
    event_update = EventUpdateKernel(random_matrix)

    with pytest.raises(ValueError, match="does not match matrix r=16"):
        event_update.update(np.zeros(15, dtype=np.uint8), [0])


@pytest.mark.parametrize("flipped_positions", [[-1], [255]])
def test_event_update_rejects_out_of_range_positions(
    random_matrix: np.ndarray,
    flipped_positions: list[int],
) -> None:
    event_update = EventUpdateKernel(random_matrix)

    with pytest.raises(ValueError, match="must be in \\[0, 255\\)"):
        event_update.update(np.zeros(16, dtype=np.uint8), flipped_positions)


def test_event_update_rejects_non_1d_positions(random_matrix: np.ndarray) -> None:
    event_update = EventUpdateKernel(random_matrix)

    with pytest.raises(ValueError, match="must be 1-D"):
        event_update.update(np.zeros(16, dtype=np.uint8), np.zeros((1, 2), dtype=np.int64))


@pytest.mark.parametrize("batch_size", [1, 4, 64, 1000])
@pytest.mark.parametrize("density", [0.01, 0.05, 0.5])
def test_packed_batch_apply_many_matches_naive(
    random_matrix: np.ndarray,
    batch_size: int,
    density: float,
) -> None:
    rng = np.random.default_rng(20260627 + batch_size)
    x_batch = (rng.random((batch_size, 255)) < density).astype(np.uint8)
    naive = NaiveGF2Kernel(random_matrix)
    packed = PackedBatchGF2Kernel(random_matrix)

    expected = naive.apply_many(x_batch)
    actual = packed.apply_many(x_batch)

    assert_unpacked_bits(actual, (batch_size, 16))
    np.testing.assert_array_equal(actual, expected)


def test_packed_batch_apply_many_rejects_wrong_width(random_matrix: np.ndarray) -> None:
    packed = PackedBatchGF2Kernel(random_matrix)

    with pytest.raises(ValueError, match="does not match matrix n=255"):
        packed.apply_many(np.zeros((4, 254), dtype=np.uint8))
