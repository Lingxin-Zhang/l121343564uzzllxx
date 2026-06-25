"""Tests for benchmark code profiles."""

from __future__ import annotations

import numpy as np
import pytest

from codes.code_profiles import get_code_profile, get_profile_matrix, list_code_profiles


@pytest.mark.parametrize(
    "name,shape,is_synthetic",
    [
        ("bch_255_239_r16", (255, 16), False),
        ("ebch_256_239_r17", (256, 17), False),
        ("synthetic_bch_like_127_r14", (127, 14), True),
        ("synthetic_511_r32", (511, 32), True),
    ],
)
def test_code_profiles_return_gf2_matrices(
    name: str,
    shape: tuple[int, int],
    is_synthetic: bool,
) -> None:
    profile = get_code_profile(name)
    matrix = get_profile_matrix(name)

    assert profile.profile_name == name
    assert (profile.n, profile.r) == shape
    assert profile.is_synthetic is is_synthetic
    assert matrix.shape == shape
    assert matrix.dtype == np.uint8
    assert set(np.unique(matrix)).issubset({0, 1})


def test_code_profile_names_are_stable() -> None:
    assert [profile.profile_name for profile in list_code_profiles()] == [
        "bch_255_239_r16",
        "ebch_256_239_r17",
        "synthetic_bch_like_127_r14",
        "synthetic_511_r32",
    ]


def test_unknown_code_profile_raises_clear_error() -> None:
    with pytest.raises(ValueError, match="unknown code profile"):
        get_code_profile("missing")
