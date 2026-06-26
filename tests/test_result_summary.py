"""Tests for result summary and paper-figure export helpers."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

from scripts.summarize_results import (
    summarize_cache_aware_selection_rows,
    summarize_cache_aware_selection_workload_rows,
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
            "test_case": "sampled_double_bit_errors",
            "syndrome_backend": "NaiveGF2Kernel.apply_many",
            "num_words": "4",
            "double_error_coverage": "sampled",
            "num_possible_double_errors": "15",
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
            "test_case": "sampled_double_bit_errors",
            "syndrome_backend": "NaiveGF2Kernel.apply_many",
            "num_words": "4",
            "double_error_coverage": "sampled",
            "num_possible_double_errors": 15,
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


def test_cache_aware_selection_summary_preserves_planner_fields() -> None:
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
            "selection_reason": "unit reason",
            "lut_bytes": "4096",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "uses_lut": "True",
            "cache_fit_applicable": "True",
            "oracle_best_backend": "PackedBlockLUTKernel",
            "oracle_best_block_width": "6",
            "selected_latency_us": "10.0",
            "oracle_best_latency_us": "8.0",
            "planner_over_oracle": "1.25",
            "correctness_passed": "True",
        }
    ]

    summary = summarize_cache_aware_selection_rows(rows)

    assert len(summary) == 1
    assert summary[0]["selected_backend"] == "PackedBlockLUTKernel"
    assert summary[0]["selected_block_width"] == "6"
    assert summary[0]["oracle_best_backend"] == "PackedBlockLUTKernel"
    assert summary[0]["mean_planner_over_oracle"] == 1.25
    assert summary[0]["correctness_all_true"] is True


def test_cache_aware_selection_workload_summary_reports_calibration_metrics() -> None:
    rows = [
        {
            "preset": "unit",
            "code_profile": "bch_255_239_r16",
            "cache_profile": "default_cpu_cache",
            "workload_type": "dense_batch",
            "batch_size": "64",
            "density_or_weight": "density=0.5",
            "output_mode": "unpacked",
            "selected_backend": "PackedBlockLUTKernel",
            "selected_block_width": "8",
            "selection_reason": "unit",
            "lut_bytes": "16384",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "uses_lut": "True",
            "cache_fit_applicable": "True",
            "oracle_best_backend": "PackedBlockLUTKernel",
            "oracle_best_block_width": "8",
            "selected_latency_us": "10.0",
            "oracle_best_latency_us": "10.0",
            "planner_over_oracle": "1.0",
            "correctness_passed": "True",
        },
        {
            "preset": "unit",
            "code_profile": "ebch_256_239_r17",
            "cache_profile": "small_l2_profile",
            "workload_type": "dense_batch",
            "batch_size": "1024",
            "density_or_weight": "density=0.5",
            "output_mode": "unpacked",
            "selected_backend": "PackedBlockLUTKernel",
            "selected_block_width": "8",
            "selection_reason": "unit",
            "lut_bytes": "32768",
            "fits_l1": "False",
            "fits_l2": "True",
            "fits_l3": "True",
            "uses_lut": "True",
            "cache_fit_applicable": "True",
            "oracle_best_backend": "PackedBatchGF2Kernel",
            "oracle_best_block_width": "0",
            "selected_latency_us": "12.0",
            "oracle_best_latency_us": "10.0",
            "planner_over_oracle": "1.2",
            "correctness_passed": "True",
        },
    ]

    summary = summarize_cache_aware_selection_workload_rows(rows)

    assert len(summary) == 1
    row = summary[0]
    assert row["preset"] == "unit"
    assert row["workload_type"] == "dense_batch"
    assert math.isclose(row["mean_planner_over_oracle"], 1.1)
    assert math.isclose(row["median_planner_over_oracle"], 1.1)
    assert math.isclose(row["p90_planner_over_oracle"], 1.18)
    assert math.isclose(row["p95_planner_over_oracle"], 1.19)
    assert math.isclose(row["max_planner_over_oracle"], 1.2)
    assert math.isclose(row["oracle_match_rate_backend_and_block"], 0.5)
    assert math.isclose(row["oracle_match_rate_backend_only"], 0.5)
    assert row["selected_backend_distribution"] == "PackedBlockLUTKernel:2"
    assert row["oracle_backend_distribution"] == "PackedBatchGF2Kernel:1;PackedBlockLUTKernel:1"
    assert row["num_rows"] == 2
    assert row["correctness_all_true"] is True


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


def test_summarize_results_cli_writes_long_stream_replication_summary(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    summary_dir = tmp_path / "summary"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "long_stream_cache_width_replication.csv",
        [
            {
                "preset": "unit",
                "code_profile": "bch_255_239_r16",
                "matrix_kind": "bch_candidate",
                "verification_status": "verified_candidate",
                "matrix_source": "galois_systematic_candidate",
                "total_bits": "4096",
                "num_words": "16",
                "iterations": "1",
                "density": "0.05",
                "block_width": "8",
                "cache_level": "L1",
                "latency_per_word_us": "10.0",
                "latency_cv": "0.01",
                "lut_bytes": "16128",
                "stream_input_bits": "4080",
                "stream_input_bytes": "510",
                "lut_over_l1": "0.49",
                "lut_over_l2": "0.015",
                "lut_over_l3": "0.001",
                "correctness_passed": "True",
            },
            {
                "preset": "unit",
                "code_profile": "bch_255_239_r16",
                "matrix_kind": "bch_candidate",
                "verification_status": "verified_candidate",
                "matrix_source": "galois_systematic_candidate",
                "total_bits": "4096",
                "num_words": "16",
                "iterations": "1",
                "density": "0.05",
                "block_width": "12",
                "cache_level": "L2",
                "latency_per_word_us": "7.0",
                "latency_cv": "0.01",
                "lut_bytes": "172048",
                "stream_input_bits": "4080",
                "stream_input_bytes": "510",
                "lut_over_l1": "5.25",
                "lut_over_l2": "0.16",
                "lut_over_l3": "0.01",
                "correctness_passed": "True",
            },
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
    summary_path = summary_dir / "long_stream_cache_width_replication_summary.csv"
    assert summary_path.exists()
    with summary_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["stream_input_bits"] == "4080"
    assert rows[0]["stream_input_bytes"] == "510"


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
