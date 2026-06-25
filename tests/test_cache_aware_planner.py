"""Tests for cache-aware backend selection rules."""

from __future__ import annotations

import numpy as np

from linear_kernel.cache_aware_planner import CacheAwarePlanner
from linear_kernel.cache_profile import CacheProfile, estimate_block_lut_bytes


def _matrix(n: int = 16, r: int = 8) -> np.ndarray:
    rng = np.random.default_rng(20260801)
    matrix = rng.integers(0, 2, size=(n, r), dtype=np.uint8)
    for bit in range(min(n, r)):
        matrix[bit, bit] = 1
    return matrix


def _cache_profile() -> CacheProfile:
    return CacheProfile(
        profile_name="unit_cache",
        l1d_bytes=512,
        l2_bytes=4096,
        l3_bytes=65536,
        cache_line_bytes=64,
        notes="unit test cache profile",
    )


def test_cache_aware_planner_selection_fields_are_complete() -> None:
    planner = CacheAwarePlanner(
        _matrix(),
        cache_profile=_cache_profile(),
        block_width_candidates=(4, 6),
    )

    selection = planner.select(
        {
            "type": "dense_batch",
            "batch_size": 64,
            "density": 0.5,
            "output_mode": "unpacked",
        }
    )

    assert selection.selected_backend
    assert selection.selected_block_width >= 0
    assert selection.selection_reason
    assert selection.lut_bytes >= 0
    assert isinstance(selection.fits_l1, bool)
    assert isinstance(selection.fits_l2, bool)
    assert isinstance(selection.fits_l3, bool)


def test_cache_aware_planner_lut_bytes_and_fit_flags_match_estimator() -> None:
    matrix = _matrix(n=10, r=8)
    cache_profile = _cache_profile()
    planner = CacheAwarePlanner(
        matrix,
        cache_profile=cache_profile,
        block_width_candidates=(4,),
    )

    selection = planner.select(
        {
            "type": "candidate_test_packed",
            "batch_size": 128,
            "candidate_count": 128,
            "output_mode": "packed",
        }
    )
    expected = estimate_block_lut_bytes(
        n=10,
        r=8,
        block_width=4,
        packed_word_bits=16,
        cache_profile=cache_profile,
    )

    assert selection.selected_backend == "PackedBlockLUTKernel"
    assert selection.selected_block_width == 4
    assert selection.lut_bytes == expected["lut_bytes"]
    assert selection.fits_l1 == expected["fits_l1"]
    assert selection.fits_l2 == expected["fits_l2"]
    assert selection.fits_l3 == expected["fits_l3"]


def test_cache_aware_planner_event_update_selects_event_update_kernel() -> None:
    planner = CacheAwarePlanner(
        _matrix(),
        cache_profile=_cache_profile(),
        block_width_candidates=(4, 6),
    )

    selection = planner.select({"type": "event_update", "batch_size": 64})

    assert selection.selected_backend == "EventUpdateKernel"
    assert selection.selected_block_width == 0
    assert selection.lut_bytes == 0
    assert "event update" in selection.selection_reason.lower()


def test_cache_aware_planner_packed_candidate_batch_uses_lut_when_cache_fits() -> None:
    planner = CacheAwarePlanner(
        _matrix(n=32, r=16),
        cache_profile=CacheProfile(
            profile_name="large_unit_cache",
            l1d_bytes=64 * 1024,
            l2_bytes=1024 * 1024,
            l3_bytes=16 * 1024 * 1024,
            cache_line_bytes=64,
            notes="large unit cache",
        ),
        block_width_candidates=(4, 6, 8),
    )

    selection = planner.select(
        {
            "type": "candidate_test_packed",
            "batch_size": 1024,
            "candidate_count": 1024,
            "output_mode": "packed",
        }
    )

    assert selection.selected_backend == "PackedBlockLUTKernel"
    assert selection.selected_block_width in {4, 6, 8}
    assert selection.fits_l2 is True
    assert "cache" in selection.selection_reason.lower()
