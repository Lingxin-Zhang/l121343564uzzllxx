"""Tests for cache profile and LUT footprint estimation."""

from __future__ import annotations

from linear_kernel.cache_profile import (
    CacheProfile,
    estimate_block_lut_bytes,
    get_cache_profile,
)


def test_default_cache_profile_has_required_fields() -> None:
    profile = get_cache_profile()

    assert profile.profile_name == "generic_desktop"
    assert profile.l1d_bytes > 0
    assert profile.l2_bytes > profile.l1d_bytes
    assert profile.l3_bytes > profile.l2_bytes
    assert profile.cache_line_bytes == 64
    assert profile.notes


def test_estimate_block_lut_bytes_handles_short_last_block() -> None:
    profile = CacheProfile(
        profile_name="tiny",
        l1d_bytes=128,
        l2_bytes=512,
        l3_bytes=4096,
        cache_line_bytes=64,
        notes="test profile",
    )

    estimate = estimate_block_lut_bytes(
        n=10,
        r=17,
        block_width=4,
        packed_word_bits=32,
        cache_profile=profile,
    )

    assert estimate["num_blocks"] == 3
    assert estimate["entries_per_block"] == 16
    assert estimate["lut_bytes"] == (16 + 16 + 4) * 4
    assert estimate["fits_l1"] is False
    assert estimate["fits_l2"] is True
    assert estimate["fits_l3"] is True


def test_cache_profile_override_fields() -> None:
    profile = get_cache_profile(
        profile_name="manual",
        l1d_bytes=48 * 1024,
        l2_bytes=2 * 1024 * 1024,
        l3_bytes=32 * 1024 * 1024,
        cache_line_bytes=128,
    )

    assert profile.profile_name == "manual"
    assert profile.l1d_bytes == 48 * 1024
    assert profile.l2_bytes == 2 * 1024 * 1024
    assert profile.l3_bytes == 32 * 1024 * 1024
    assert profile.cache_line_bytes == 128
