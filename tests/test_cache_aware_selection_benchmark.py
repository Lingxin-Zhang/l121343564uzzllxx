"""Tests for cache-aware selection benchmark helpers."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from benchmarks.bench_cache_aware_selection import (
    CACHE_AWARE_SELECTION_FIELDNAMES,
    run_cache_aware_selection_rows,
)
from scripts.plot_experiment_round06_results import plot_cache_aware_selection


def test_cache_aware_selection_rows_are_correct_and_complete() -> None:
    rows = run_cache_aware_selection_rows(
        preset="unit",
        code_profiles=("bch_255_239_r16",),
        cache_profiles=("default_cpu_cache",),
        workload_types=("sparse_single", "candidate_test_packed", "event_update"),
        batch_sizes=(1, 64),
        block_width_candidates=(4, 6),
        repeats=1,
    )

    assert rows
    assert all(set(CACHE_AWARE_SELECTION_FIELDNAMES) >= set(row) for row in rows)
    assert all(row["selected_backend"] for row in rows)
    assert all(row["selected_block_width"] != "" for row in rows)
    assert all(row["selection_reason"] for row in rows)
    assert all(row["correctness_passed"] is True for row in rows)
    assert all(math.isfinite(float(row["planner_over_oracle"])) for row in rows)
    assert all(float(row["planner_over_oracle"]) > 0.0 for row in rows)


def test_cache_aware_selection_plot_reads_new_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "cache_aware_selection.csv"
    figure_dir = tmp_path / "figures"
    rows = [
        {
            "preset": "unit",
            "code_profile": "bch_255_239_r16",
            "n": "255",
            "r": "16",
            "cache_profile": "default_cpu_cache",
            "workload_type": "candidate_test_packed",
            "batch_size": "64",
            "density_or_weight": "0.05",
            "output_mode": "packed",
            "selected_backend": "PackedBlockLUTKernel",
            "selected_block_width": "6",
            "selection_reason": "unit",
            "lut_bytes": "4096",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "oracle_best_backend": "PackedBlockLUTKernel",
            "oracle_best_block_width": "6",
            "selected_latency_us": "10.0",
            "oracle_best_latency_us": "8.0",
            "planner_over_oracle": "1.25",
            "correctness_passed": "True",
        }
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CACHE_AWARE_SELECTION_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    plot_cache_aware_selection(csv_path=csv_path, figure_dir=figure_dir)

    assert (figure_dir / "experiment_round06_cache_aware_selection.png").exists()
    assert (figure_dir / "experiment_round06_cache_aware_selection.pdf").exists()
