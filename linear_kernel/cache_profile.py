"""Cache-profile helpers for benchmark planning and reporting."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CacheProfile:
    """Simple CPU-cache metadata used for LUT footprint reporting."""

    profile_name: str
    l1d_bytes: int
    l2_bytes: int
    l3_bytes: int
    cache_line_bytes: int
    notes: str


def _read_int_env(name: str, fallback: int) -> int:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return fallback
    return int(value)


def get_cache_profile(
    *,
    profile_name: str = "generic_desktop",
    l1d_bytes: int | None = None,
    l2_bytes: int | None = None,
    l3_bytes: int | None = None,
    cache_line_bytes: int | None = None,
    notes: str = "generic manually configurable cache profile",
) -> CacheProfile:
    """Return cache metadata with optional explicit/env overrides."""

    l1d = int(l1d_bytes) if l1d_bytes is not None else _read_int_env("GF2_L1D_BYTES", 32 * 1024)
    l2 = int(l2_bytes) if l2_bytes is not None else _read_int_env("GF2_L2_BYTES", 1024 * 1024)
    l3 = int(l3_bytes) if l3_bytes is not None else _read_int_env("GF2_L3_BYTES", 16 * 1024 * 1024)
    line = (
        int(cache_line_bytes)
        if cache_line_bytes is not None
        else _read_int_env("GF2_CACHE_LINE_BYTES", 64)
    )
    if min(l1d, l2, l3, line) <= 0:
        raise ValueError("cache sizes and cache_line_bytes must be positive")
    return CacheProfile(
        profile_name=profile_name,
        l1d_bytes=l1d,
        l2_bytes=l2,
        l3_bytes=l3,
        cache_line_bytes=line,
        notes=notes,
    )


def estimate_block_lut_bytes(
    n: int,
    r: int,
    block_width: int,
    packed_word_bits: int,
    cache_profile: CacheProfile | None = None,
) -> dict[str, Any]:
    """Estimate packed block-LUT table bytes and cache fit flags."""

    n = int(n)
    r = int(r)
    block_width = int(block_width)
    packed_word_bits = int(packed_word_bits)
    if n <= 0 or r <= 0:
        raise ValueError("n and r must be positive")
    if block_width <= 0:
        raise ValueError("block_width must be positive")
    if packed_word_bits not in (16, 32):
        raise ValueError("packed_word_bits must be 16 or 32")
    if r > packed_word_bits:
        raise ValueError("r cannot exceed packed_word_bits")

    entry_bytes = packed_word_bits // 8
    num_blocks = (n + block_width - 1) // block_width
    lut_bytes = 0
    max_entries = 0
    for start in range(0, n, block_width):
        width = min(block_width, n - start)
        entries = 1 << width
        max_entries = max(max_entries, entries)
        lut_bytes += entries * entry_bytes

    profile = cache_profile or get_cache_profile()
    return {
        "num_blocks": num_blocks,
        "entries_per_block": max_entries,
        "lut_bytes": lut_bytes,
        "fits_l1": lut_bytes <= profile.l1d_bytes,
        "fits_l2": lut_bytes <= profile.l2_bytes,
        "fits_l3": lut_bytes <= profile.l3_bytes,
    }
