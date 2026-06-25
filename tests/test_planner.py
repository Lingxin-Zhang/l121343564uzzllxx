"""Tests for the simple workload-aware HybridPlanner."""

from __future__ import annotations

import numpy as np
import pytest

from codes.matrix_sources import get_matrix_source
from linear_kernel import HybridPlanner, NaiveGF2Kernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16


@pytest.fixture(scope="module")
def candidate_matrix() -> np.ndarray:
    pytest.importorskip("galois")
    return get_matrix_source("galois_systematic_candidate")


def test_planner_apply_matches_naive(candidate_matrix: np.ndarray) -> None:
    rng = np.random.default_rng(20260710)
    planner = HybridPlanner(candidate_matrix, sparse_threshold=8)
    naive = NaiveGF2Kernel(candidate_matrix)

    for weight in (2, 16):
        x = np.zeros(255, dtype=np.uint8)
        x[rng.choice(255, size=weight, replace=False)] = 1
        np.testing.assert_array_equal(planner.apply(x), naive.apply(x))


def test_planner_apply_many_matches_naive(candidate_matrix: np.ndarray) -> None:
    rng = np.random.default_rng(20260711)
    x_batch = (rng.random((128, 255)) < 0.05).astype(np.uint8)
    planner = HybridPlanner(candidate_matrix, batch_threshold=64)
    naive = NaiveGF2Kernel(candidate_matrix)

    np.testing.assert_array_equal(planner.apply_many(x_batch), naive.apply_many(x_batch))


def test_planner_apply_many_packed_matches_packed_naive(candidate_matrix: np.ndarray) -> None:
    rng = np.random.default_rng(20260712)
    x_batch = (rng.random((128, 255)) < 0.05).astype(np.uint8)
    planner = HybridPlanner(candidate_matrix, batch_threshold=64)
    naive = NaiveGF2Kernel(candidate_matrix)

    expected = pack_batch_bits_to_uint16(naive.apply_many(x_batch))
    actual = planner.apply_many_packed(x_batch)

    assert actual.dtype == np.uint16
    assert actual.shape == (128,)
    np.testing.assert_array_equal(actual, expected)


@pytest.mark.parametrize("flip_count", [1, 2, 4])
def test_planner_update_many_matches_from_scratch(
    candidate_matrix: np.ndarray,
    flip_count: int,
) -> None:
    rng = np.random.default_rng(20260713 + flip_count)
    x_batch = (rng.random((16, 255)) < 0.05).astype(np.uint8)
    flipped_positions = np.stack(
        [rng.choice(255, size=flip_count, replace=False) for _ in range(16)],
        axis=0,
    ).astype(np.int64)
    x_flipped = x_batch.copy()
    rows = np.repeat(np.arange(16), flip_count)
    cols = flipped_positions.reshape(-1)
    x_flipped[rows, cols] ^= 1

    planner = HybridPlanner(candidate_matrix)
    naive = NaiveGF2Kernel(candidate_matrix)
    old_syndromes = naive.apply_many(x_batch)

    np.testing.assert_array_equal(
        planner.update_many(old_syndromes, flipped_positions),
        naive.apply_many(x_flipped),
    )
