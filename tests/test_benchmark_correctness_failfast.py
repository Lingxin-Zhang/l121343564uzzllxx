"""Tests that benchmark helpers fail fast on correctness mismatches."""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks.bench_candidate_testing import assert_outputs_match
from benchmarks.bench_cache_aware import assert_correct
from benchmarks.bench_code_profiles import assert_backend_correct


def test_cache_aware_assert_correct_raises_on_mismatch() -> None:
    expected = np.zeros((2, 3), dtype=np.uint8)
    actual = expected.copy()
    actual[0, 0] = 1

    with pytest.raises(AssertionError, match="cache-aware correctness failed"):
        assert_correct("bad_backend", actual, expected, context="unit")


def test_code_profile_assert_correct_raises_on_mismatch() -> None:
    expected = np.zeros((2, 3), dtype=np.uint8)
    actual = expected.copy()
    actual[1, 2] = 1

    with pytest.raises(AssertionError, match="code-profile correctness failed"):
        assert_backend_correct("bad_backend", actual, expected, context="unit")


def test_candidate_testing_assert_outputs_match_raises_on_mismatch() -> None:
    expected = np.zeros((2, 3), dtype=np.uint8)
    actual = expected.copy()
    actual[0, 1] = 1

    with pytest.raises(AssertionError, match="candidate testing correctness failed"):
        assert_outputs_match("bad_backend", actual, expected, context="unit")
