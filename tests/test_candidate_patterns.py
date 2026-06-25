"""Tests for deterministic candidate error-pattern generation."""

from __future__ import annotations

import numpy as np

from workloads.candidate_patterns import (
    make_chase_ii_patterns,
    make_fixed_weight_patterns,
)


def test_chase_ii_patterns_enumerate_all_combinations() -> None:
    patterns = make_chase_ii_patterns(n=10, p_chase=3, positions=[2, 4, 7])

    assert patterns.shape == (8, 10)
    assert patterns.dtype == np.uint8
    assert set(np.unique(patterns).tolist()) <= {0, 1}
    assert np.all(patterns[:, [0, 1, 3, 5, 6, 8, 9]] == 0)
    assert sorted(patterns[:, [2, 4, 7]].sum(axis=1).tolist()) == [0, 1, 1, 1, 2, 2, 2, 3]


def test_fixed_weight_patterns_have_requested_weight_and_seed_stability() -> None:
    first = make_fixed_weight_patterns(n=16, candidate_weight=4, candidate_count=32, seed=123)
    second = make_fixed_weight_patterns(n=16, candidate_weight=4, candidate_count=32, seed=123)

    assert first.shape == (32, 16)
    assert first.dtype == np.uint8
    assert set(np.unique(first).tolist()) <= {0, 1}
    assert np.all(first.sum(axis=1) == 4)
    np.testing.assert_array_equal(first, second)


def test_fixed_weight_zero_returns_all_zero_patterns() -> None:
    patterns = make_fixed_weight_patterns(n=12, candidate_weight=0, candidate_count=5, seed=7)

    assert patterns.shape == (5, 12)
    assert not patterns.any()
