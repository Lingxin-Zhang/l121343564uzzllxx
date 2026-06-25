"""Tests for result summary and paper-figure export helpers."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

from scripts.summarize_results import (
    summarize_component_decoder_exactness_rows,
    summarize_component_loop_rows,
    summarize_event_update_rows,
    summarize_optical_workload_rows,
)


def test_component_loop_summary_computes_mean_and_relative_to_naive() -> None:
    rows = [
        {
            "matrix_source": "galois_systematic_candidate",
            "backend": "Naive.apply_many",
            "num_words": "8",
            "iterations": "1",
            "latency_per_word_us": "10.0",
            "throughput_Mword_s": "1.0",
            "throughput_Mbit_s": "255.0",
            "table_size_bytes": "0",
            "correctness_passed": "True",
        },
        {
            "matrix_source": "galois_systematic_candidate",
            "backend": "PackedBlockLUT.apply_many_packed",
            "num_words": "8",
            "iterations": "1",
            "latency_per_word_us": "5.0",
            "throughput_Mword_s": "2.0",
            "throughput_Mbit_s": "510.0",
            "table_size_bytes": "4096",
            "correctness_passed": "True",
        },
    ]

    summary = summarize_component_loop_rows(rows)
    packed = next(
        row
        for row in summary
        if row["backend"] == "PackedBlockLUT.apply_many_packed"
    )

    assert packed["mean_latency_per_word_us"] == 5.0
    assert packed["relative_to_naive"] == 2.0
    assert packed["correctness_all_true"] is True
    assert packed["num_rows"] == 1


def test_event_update_summary_handles_missing_baseline_without_crashing() -> None:
    rows = [
        {
            "matrix_source": "galois_systematic_candidate",
            "method": "event_update.batch_update_many",
            "flip_count": "1",
            "iterations": "1",
            "latency_per_word_us": "3.0",
            "throughput_Mupdate_s": "5.0",
            "correctness_passed": "True",
        }
    ]

    summary = summarize_event_update_rows(rows)

    assert len(summary) == 1
    assert math.isnan(summary[0]["relative_to_from_scratch_packed"])
    assert summary[0]["correctness_all_true"] is True


def test_component_decoder_exactness_summary_reports_zero_mismatch() -> None:
    rows = [
        {
            "preset": "unit",
            "code_profile": "unit_profile",
            "test_case": "all_single_bit_errors",
            "syndrome_backend": "NaiveGF2Kernel.apply_many",
            "num_words": "4",
            "exact_mismatch_count": "0",
            "latency_per_word_us": "2.0",
            "throughput_Mword_s": "0.5",
            "correctness_passed": "True",
        }
    ]

    summary = summarize_component_decoder_exactness_rows(rows)

    assert summary == [
        {
            "preset": "unit",
            "code_profile": "unit_profile",
            "test_case": "all_single_bit_errors",
            "syndrome_backend": "NaiveGF2Kernel.apply_many",
            "num_words": "4",
            "exact_mismatch_count": 0,
            "correctness_all_true": True,
            "mean_latency_per_word_us": 2.0,
            "mean_throughput_Mword_s": 0.5,
            "num_rows": 1,
        }
    ]


def test_optical_summary_prefers_executed_unit_metrics() -> None:
    rows = [
        {
            "preset": "unit",
            "workload_type": "ofec_like",
            "code_profile": "unit_profile",
            "num_blocks": "2",
            "window_len": "2",
            "num_iterations_or_steps": "1",
            "backend_or_method": "Naive+EventUpdate.integrated",
            "block_width": "4",
            "batch_size": "4",
            "density": "0.05",
            "intended_syndrome_calls": "2",
            "executed_syndrome_calls": "2",
            "intended_candidate_tests": "512",
            "executed_candidate_tests": "32",
            "intended_event_updates": "2",
            "executed_event_updates": "2",
            "num_syndrome_calls": "2",
            "num_candidate_tests": "512",
            "num_executed_candidate_tests": "32",
            "num_event_updates": "2",
            "total_runtime_s": "0.001",
            "latency_per_component_us": "999.0",
            "throughput_Mcomponent_s": "0.001",
            "aggregate_latency_per_executed_unit_us": "27.7777777778",
            "throughput_Mexecuted_unit_s": "0.036",
            "correctness_passed": "True",
            "notes": "unit",
        }
    ]

    summary = summarize_optical_workload_rows(rows)

    assert len(summary) == 1
    assert "mean_latency_per_component_us" not in summary[0]
    assert summary[0]["mean_aggregate_latency_per_executed_unit_us"] == 27.7777777778
    assert summary[0]["mean_throughput_Mexecuted_unit_s"] == 0.036
    assert summary[0]["executed_candidate_tests"] == 32
    assert summary[0]["correctness_all_true"] is True


def test_summarize_results_cli_writes_summary_files(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    summary_dir = tmp_path / "summary"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "component_loop.csv",
        [
            {
                "matrix_source": "galois_systematic_candidate",
                "backend": "Naive.apply_many",
                "num_words": "8",
                "iterations": "1",
                "latency_per_word_us": "10.0",
                "throughput_Mword_s": "1.0",
                "throughput_Mbit_s": "255.0",
                "table_size_bytes": "0",
                "correctness_passed": "True",
            }
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_results.py",
            "--raw-dir",
            str(raw_dir),
            "--summary-dir",
            str(summary_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert (summary_dir / "component_loop_summary.csv").exists()


def test_summary_and_export_help_run() -> None:
    for script in ("scripts/summarize_results.py", "scripts/export_paper_figures.py"):
        result = subprocess.run(
            [sys.executable, script, "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
