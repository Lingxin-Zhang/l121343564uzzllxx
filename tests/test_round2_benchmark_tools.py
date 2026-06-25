"""Tests for Round 2 benchmark helpers and summary output."""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

from scripts.summarize_results import summarize_cache_aware_rows


def test_cache_aware_summary_groups_rows() -> None:
    rows = [
        {
            "preset": "lightweight",
            "code_profile": "synthetic_511_r32",
            "n": "511",
            "r": "32",
            "backend": "PackedBlockLUT.apply_many_packed",
            "block_width": "8",
            "batch_size": "64",
            "density": "0.05",
            "lut_bytes": "16384",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "latency_per_word_us": "2.0",
            "throughput_Mword_s": "0.5",
            "mean": "0.000128",
            "std": "0.000001",
            "repeats": "3",
            "correctness_passed": "True",
        },
        {
            "preset": "lightweight",
            "code_profile": "synthetic_511_r32",
            "n": "511",
            "r": "32",
            "backend": "PackedBlockLUT.apply_many_packed",
            "block_width": "8",
            "batch_size": "64",
            "density": "0.05",
            "lut_bytes": "16384",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "latency_per_word_us": "4.0",
            "throughput_Mword_s": "0.25",
            "mean": "0.000256",
            "std": "0.000002",
            "repeats": "3",
            "correctness_passed": "True",
        },
    ]

    summary = summarize_cache_aware_rows(rows)

    assert len(summary) == 1
    assert summary[0]["mean_latency_per_word_us"] == 3.0
    assert summary[0]["correctness_all_true"] is True
    assert summary[0]["num_rows"] == 2


def test_round2_benchmark_help_runs() -> None:
    for module in (
        "benchmarks.bench_cache_aware",
        "benchmarks.bench_code_profiles",
        "benchmarks.bench_candidate_testing",
        "benchmarks.bench_optical_workloads",
    ):
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower()


def test_summarize_results_writes_round2_outputs(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    summary_dir = tmp_path / "summary"
    raw_dir.mkdir()
    _write_csv(
        raw_dir / "cache_aware.csv",
        [
            {
                "preset": "lightweight",
                "code_profile": "synthetic_511_r32",
                "n": "511",
                "r": "32",
                "backend": "Naive.apply_many",
                "block_width": "8",
                "batch_size": "64",
                "density": "0.05",
                "lut_bytes": "0",
                "fits_l1": "True",
                "fits_l2": "True",
                "fits_l3": "True",
                "latency_per_word_us": "1.0",
                "throughput_Mword_s": "1.0",
                "mean": "0.000064",
                "std": "0.0",
                "repeats": "3",
                "correctness_passed": "True",
            }
        ],
    )
    _write_csv(
        raw_dir / "candidate_testing.csv",
        [
            {
                "preset": "lightweight",
                "code_profile": "bch_255_239_r16",
                "n": "255",
                "r": "16",
                "pattern_type": "fixed_weight",
                "p_chase": "0",
                "candidate_weight": "2",
                "candidate_count": "256",
                "backend": "Naive.apply_many",
                "batch_size": "256",
                "block_width": "8",
                "packed_word_bits": "16",
                "latency_per_candidate_us": "1.0",
                "throughput_Mcandidate_s": "1.0",
                "matches_found": "0",
                "mean": "0.000256",
                "std": "0.0",
                "repeats": "3",
                "correctness_passed": "True",
            }
        ],
    )
    _write_csv(
        raw_dir / "optical_workloads.csv",
        [
            {
                "preset": "lightweight",
                "workload_type": "product_like",
                "code_profile": "bch_255_239_r16",
                "n": "255",
                "r": "16",
                "num_blocks": "8",
                "window_len": "4",
                "num_iterations_or_steps": "1",
                "num_syndrome_calls": "16",
                "num_candidate_tests": "0",
                "num_event_updates": "0",
                "backend_or_method": "Naive.apply_many",
                "block_width": "8",
                "batch_size": "64",
                "density": "0.05",
                "total_runtime_s": "0.001",
                "latency_per_component_us": "1.0",
                "throughput_Mcomponent_s": "1.0",
                "mean": "0.001",
                "std": "0.0",
                "repeats": "3",
                "correctness_passed": "True",
                "notes": "trace-level workload only; no BER; no full decoder",
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
    assert (summary_dir / "cache_aware_summary.csv").exists()
    assert (summary_dir / "candidate_testing_summary.csv").exists()
    assert (summary_dir / "optical_workloads_summary.csv").exists()


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
