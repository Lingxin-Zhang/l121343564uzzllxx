"""Tests for named benchmark matrix sources."""

from __future__ import annotations

import numpy as np
import pytest

from codes.matrix_sources import get_matrix_source


def assert_gf2_matrix(matrix: np.ndarray) -> None:
    assert matrix.shape == (255, 16)
    assert matrix.dtype == np.uint8
    assert set(np.unique(matrix)).issubset({0, 1})


def test_placeholder_matrix_source_returns_gf2_matrix() -> None:
    assert_gf2_matrix(get_matrix_source("placeholder"))


def test_galois_systematic_candidate_matrix_source_returns_gf2_matrix() -> None:
    pytest.importorskip("galois")

    assert_gf2_matrix(get_matrix_source("galois_systematic_candidate"))


def test_random_fixed_matrix_source_is_deterministic() -> None:
    first = get_matrix_source("random_fixed")
    second = get_matrix_source("random_fixed")

    assert_gf2_matrix(first)
    np.testing.assert_array_equal(first, second)


def test_unknown_matrix_source_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown matrix source"):
        get_matrix_source("not_a_source")
