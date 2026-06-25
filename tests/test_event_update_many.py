"""Tests for batch event-driven syndrome updates."""

from __future__ import annotations

import numpy as np
import pytest

from linear_kernel import EventUpdateKernel, NaiveGF2Kernel


@pytest.fixture(scope="module")
def matrix() -> np.ndarray:
    rng = np.random.default_rng(20260708)
    return rng.integers(0, 2, size=(255, 16), dtype=np.uint8)


def _flip_batch(x_batch: np.ndarray, flipped_positions: np.ndarray) -> np.ndarray:
    flipped = x_batch.copy()
    if flipped_positions.shape[1] == 0:
        return flipped
    rows = np.repeat(np.arange(x_batch.shape[0]), flipped_positions.shape[1])
    cols = flipped_positions.reshape(-1)
    flipped[rows, cols] ^= 1
    return flipped


@pytest.mark.parametrize("batch_size", [1, 16])
@pytest.mark.parametrize("flip_count", [0, 1, 2, 4])
def test_update_many_matches_single_update_and_from_scratch(
    matrix: np.ndarray,
    batch_size: int,
    flip_count: int,
) -> None:
    rng = np.random.default_rng(20260709 + batch_size + flip_count)
    x_batch = rng.integers(0, 2, size=(batch_size, 255), dtype=np.uint8)
    flipped_positions = np.stack(
        [rng.choice(255, size=flip_count, replace=False) for _ in range(batch_size)],
        axis=0,
    ).astype(np.int64)

    naive = NaiveGF2Kernel(matrix)
    event = EventUpdateKernel(matrix)
    current_values = naive.apply_many(x_batch)
    current_before = current_values.copy()
    x_flipped = _flip_batch(x_batch, flipped_positions)

    actual = event.update_many(current_values, flipped_positions)
    expected_from_loop = np.stack(
        [
            event.update(current, positions)
            for current, positions in zip(current_values, flipped_positions, strict=True)
        ],
        axis=0,
    )
    expected_from_scratch = naive.apply_many(x_flipped)

    assert actual.dtype == np.uint8
    assert actual.shape == (batch_size, 16)
    np.testing.assert_array_equal(actual, expected_from_loop)
    np.testing.assert_array_equal(actual, expected_from_scratch)
    np.testing.assert_array_equal(current_values, current_before)


def test_update_many_rejects_invalid_current_values_shape(matrix: np.ndarray) -> None:
    event = EventUpdateKernel(matrix)

    with pytest.raises(ValueError, match="current_values must be 2-D"):
        event.update_many(np.zeros(16, dtype=np.uint8), np.zeros((1, 1), dtype=np.int64))

    with pytest.raises(ValueError, match="does not match matrix r=16"):
        event.update_many(np.zeros((2, 15), dtype=np.uint8), np.zeros((2, 1), dtype=np.int64))


def test_update_many_rejects_invalid_position_shape(matrix: np.ndarray) -> None:
    event = EventUpdateKernel(matrix)
    current_values = np.zeros((2, 16), dtype=np.uint8)

    with pytest.raises(ValueError, match="flipped_positions must be 2-D"):
        event.update_many(current_values, np.zeros(2, dtype=np.int64))

    with pytest.raises(ValueError, match="batch size"):
        event.update_many(current_values, np.zeros((3, 1), dtype=np.int64))


def test_update_many_rejects_invalid_positions(matrix: np.ndarray) -> None:
    event = EventUpdateKernel(matrix)
    current_values = np.zeros((2, 16), dtype=np.uint8)

    with pytest.raises(ValueError, match="integer positions"):
        event.update_many(current_values, np.zeros((2, 1), dtype=np.float64))

    with pytest.raises(ValueError, match="must be in \\[0, 255\\)"):
        event.update_many(current_values, np.array([[0], [255]], dtype=np.int64))
