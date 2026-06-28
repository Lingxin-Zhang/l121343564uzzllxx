"""Round 32 cache-counter probe and fallback rows.

This module intentionally performs read-only capability checks. On Windows in
this workspace, Linux ``perf``/``perf_event_open`` style counters are not
available, so the benchmark emits an explicit cache-fit fallback instead of
fabricating cache-miss counts.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from benchmarks._common import RAW_DIR, ensure_result_dirs
from benchmarks.bench_round31_cache_width import PROFILE_PARAMS, cache_level_fit, lut_table_bytes
from linear_kernel.cache_profile import get_cache_profile

DEFAULT_BLOCK_WIDTHS = tuple(range(4, 27))
DEFAULT_BATCH_SIZES = (100, 1_000, 100_000)
DEFAULT_OUTPUT = RAW_DIR / "round32_cache_counter_probe.csv"
CACHE_ORDINAL = {"L1": 1, "L2": 2, "L3": 3, "DRAM": 4}

FIELDNAMES = [
    "profile",
    "n",
    "k",
    "r",
    "block_width",
    "batch_size",
    "lut_table_bytes",
    "cache_level_fit",
    "cache_level_ordinal",
    "table_lookups_per_codeword",
    "theoretical_ops",
    "counter_mode",
    "perf_available",
    "perf_event_paranoid",
    "typeperf_available",
    "counter_events",
    "l1_misses_per_bit",
    "l2_misses_per_bit",
    "llc_misses_per_bit",
    "cycles_per_bit",
    "notes",
]


def probe_counter_capability() -> dict[str, str]:
    perf_path = shutil.which("perf")
    taskset_path = shutil.which("taskset")
    typeperf_path = shutil.which("typeperf")
    paranoid_path = Path("/proc/sys/kernel/perf_event_paranoid")
    perf_event_paranoid = ""
    if paranoid_path.exists():
        perf_event_paranoid = paranoid_path.read_text(encoding="utf-8", errors="replace").strip()

    cache_events: list[str] = []
    if perf_path:
        try:
            listing = subprocess.run(
                [perf_path, "list"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            text = (listing.stdout or "") + (listing.stderr or "")
            for event in ("L1-dcache-load-misses", "LLC-load-misses", "l2_rqsts.miss"):
                if event.lower() in text.lower():
                    cache_events.append(event)
        except Exception:
            cache_events = []

    return {
        "perf_available": "yes" if perf_path else "no",
        "taskset_available": "yes" if taskset_path else "no",
        "typeperf_available": "yes" if typeperf_path else "no",
        "perf_event_paranoid": perf_event_paranoid or "not_found",
        "counter_events": ";".join(cache_events),
    }


def _cache_sizes_from_profile(cache_sizes: dict[str, int] | None) -> dict[str, int]:
    if cache_sizes is not None:
        return cache_sizes
    cache = get_cache_profile()
    return {"l1d_bytes": int(cache.l1d_bytes), "l2_bytes": int(cache.l2_bytes), "l3_bytes": int(cache.l3_bytes)}


def _profile_items(
    profiles: tuple[str, ...],
    profile_params: dict[str, tuple[int, int, str]] | None,
) -> list[tuple[str, int, int, str]]:
    params = profile_params or PROFILE_PARAMS
    items = []
    for key in profiles:
        if key not in params:
            raise ValueError(f"unknown profile {key!r}")
        n, k, label = params[key]
        items.append((key, int(n), int(k), str(label)))
    return items


def build_cache_probe_rows(
    *,
    profiles: tuple[str, ...],
    block_widths: tuple[int, ...] = DEFAULT_BLOCK_WIDTHS,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    profile_params: dict[str, tuple[int, int, str]] | None = None,
    cache_sizes: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    capability = probe_counter_capability()
    sizes = _cache_sizes_from_profile(cache_sizes)
    hardware_counter_available = capability["perf_available"] == "yes" and bool(capability["counter_events"])
    counter_mode = "perf_event_open" if hardware_counter_available else "cache_fit_fallback"
    rows: list[dict[str, Any]] = []

    for _key, n, k, label in _profile_items(profiles, profile_params):
        r = n - k
        for width in block_widths:
            table_bytes = lut_table_bytes(n, r, width)
            level = cache_level_fit(table_bytes)
            for batch_size in batch_sizes:
                rows.append(
                    {
                        "profile": label,
                        "n": n,
                        "k": k,
                        "r": r,
                        "block_width": int(width),
                        "batch_size": int(batch_size),
                        "lut_table_bytes": int(table_bytes),
                        "cache_level_fit": level,
                        "cache_level_ordinal": CACHE_ORDINAL.get(level, 4),
                        "table_lookups_per_codeword": int(math.ceil(n / width)),
                        "theoretical_ops": int((width + r) * math.ceil(n / width)),
                        "counter_mode": counter_mode,
                        "perf_available": capability["perf_available"],
                        "perf_event_paranoid": capability["perf_event_paranoid"],
                        "typeperf_available": capability["typeperf_available"],
                        "counter_events": capability["counter_events"],
                        "l1_misses_per_bit": "",
                        "l2_misses_per_bit": "",
                        "llc_misses_per_bit": "",
                        "cycles_per_bit": "",
                        "notes": (
                            "hardware cache-miss counters unavailable; using cache-fit boundary fallback"
                            if not hardware_counter_available
                            else "hardware counter path detected but not used by this fallback builder"
                        ),
                        "l1d_bytes": int(sizes["l1d_bytes"]),
                        "l2_bytes": int(sizes["l2_bytes"]),
                        "l3_bytes": int(sizes["l3_bytes"]),
                    }
                )
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*FIELDNAMES, "l1d_bytes", "l2_bytes", "l3_bytes"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_ints(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_profiles(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe Round32 cache-counter availability and emit fallback rows.")
    parser.add_argument("--profiles", default=",".join(PROFILE_PARAMS))
    parser.add_argument("--block-widths", default=",".join(str(v) for v in DEFAULT_BLOCK_WIDTHS))
    parser.add_argument("--batch-sizes", default=",".join(str(v) for v in DEFAULT_BATCH_SIZES))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = build_cache_probe_rows(
        profiles=_parse_profiles(args.profiles),
        block_widths=_parse_ints(args.block_widths),
        batch_sizes=_parse_ints(args.batch_sizes),
    )
    write_rows(args.output, rows)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
