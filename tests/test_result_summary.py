"""Tests for result summary and paper-figure export helpers."""

from __future__ import annotations

import csv
import math
import subprocess
import sys
from pathlib import Path

from scripts.summarize_results import (
    summarize_component_loop_rows,
    summarize_event_update_rows,
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
