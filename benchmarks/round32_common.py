"""Shared Round32 benchmark helpers."""

from __future__ import annotations

import csv
import time
from pathlib import Path
from typing import Any


def frequency_probe_ns_per_iter(iterations: int = 200_000) -> float:
    """Return a small CPU-bound timing probe in ns/iteration.

    The value is a software frequency proxy, not a hardware frequency readout.
    Higher values mean the calibration loop ran slower at that moment.
    """

    value = 0x12345678
    start = time.perf_counter()
    for idx in range(int(iterations)):
        value = ((value ^ idx) * 1664525 + 1013904223) & 0xFFFFFFFF
    elapsed = time.perf_counter() - start
    # Keep the loop value live so Python cannot trivially discard the work.
    if value == -1:
        raise RuntimeError("unreachable probe value")
    return elapsed * 1_000_000_000.0 / max(1, int(iterations))


def annotate_probe_fields(rows: list[dict[str, Any]], *, round_index: int, probe_iterations: int) -> list[dict[str, Any]]:
    before = frequency_probe_ns_per_iter(probe_iterations)
    # Rows are already measured by the caller; this helper is intentionally used
    # after measurement to record the local post-scan probe as well.
    after = frequency_probe_ns_per_iter(probe_iterations)
    probe = (before + after) / 2.0
    annotated: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        copied["round_index"] = int(round_index)
        copied["probe_iterations"] = int(probe_iterations)
        copied["probe_before_ns_per_iter"] = before
        copied["probe_after_ns_per_iter"] = after
        copied["probe_ns_per_iter"] = probe
        copied["throughput_norm_Mbit_s"] = row.get("throughput_Mbit_s", "")
        copied["normalization_note"] = "coarse per-round probe recorded; normalized field equals raw pending cross-round reference"
        annotated.append(copied)
    return annotated


def normalize_rows_by_probe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    probes = []
    for row in rows:
        try:
            probes.append(float(row["probe_ns_per_iter"]))
        except Exception:
            pass
    if not probes:
        return rows
    reference = sorted(probes)[len(probes) // 2]
    normalized = []
    for row in rows:
        copied = dict(row)
        try:
            probe = float(copied["probe_ns_per_iter"])
            throughput = float(copied["throughput_Mbit_s"])
            copied["throughput_norm_Mbit_s"] = throughput * probe / reference
            copied["normalization_reference_probe_ns_per_iter"] = reference
            copied["normalization_note"] = "throughput scaled by row_probe/reference_probe"
        except Exception:
            copied["normalization_reference_probe_ns_per_iter"] = reference
        normalized.append(copied)
    return normalized


def write_dynamic_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
