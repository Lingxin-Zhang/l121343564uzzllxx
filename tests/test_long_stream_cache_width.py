from __future__ import annotations

import math
import csv
from pathlib import Path

from benchmarks.bench_long_stream_cache_width import (
    LONG_STREAM_CACHE_WIDTH_FIELDNAMES,
    cache_level_from_fit,
    run_long_stream_cache_width_rows,
)
from scripts.plot_experiment_round09_results import plot_long_stream_cache_width
from scripts.summarize_results import summarize_long_stream_cache_width_rows


REQUIRED_FIELDS = {
    "preset",
    "code_profile",
    "matrix_kind",
    "verification_status",
    "matrix_source",
    "matrix_shape",
    "component_n",
    "output_r",
    "total_bits",
    "num_words",
    "chunk_words",
    "iterations",
    "density",
    "block_width",
    "packed_word_bits",
    "lut_bytes",
    "fits_l1",
    "fits_l2",
    "fits_l3",
    "cache_level",
    "latency_per_word_us",
    "latency_per_word_std_us",
    "latency_cv",
    "throughput_Mbit_s",
    "repeats",
    "mean",
    "std",
    "correctness_passed",
}


def test_cache_level_from_fit_prefers_smallest_cache_that_fits() -> None:
    assert cache_level_from_fit(True, True, True) == "L1"
    assert cache_level_from_fit(False, True, True) == "L2"
    assert cache_level_from_fit(False, False, True) == "L3"
    assert cache_level_from_fit(False, False, False) == "memory"


def test_long_stream_cache_width_rows_are_correct_and_complete() -> None:
    rows = run_long_stream_cache_width_rows(
        preset="unit",
        matrix_source="galois_systematic_candidate",
        total_bits_values=(4096,),
        iterations_values=(1,),
        block_widths=(4, 8, 12),
        density=0.05,
        chunk_words=32,
        repeats=1,
    )

    assert len(rows) == 3
    assert set(LONG_STREAM_CACHE_WIDTH_FIELDNAMES) >= REQUIRED_FIELDS
    for row in rows:
        assert REQUIRED_FIELDS <= set(row)
        assert row["matrix_shape"] == "255x16"
        assert row["component_n"] == 255
        assert row["output_r"] == 16
        assert row["num_words"] == 16
        assert row["correctness_passed"] is True
        assert row["latency_per_word_us"] > 0
        assert row["throughput_Mbit_s"] > 0


def test_long_stream_cache_width_can_sweep_code_profiles() -> None:
    rows = run_long_stream_cache_width_rows(
        preset="unit",
        code_profiles=("bch_255_239_r16", "ebch_256_239_r17"),
        total_bits_values=(4096,),
        iterations_values=(1,),
        block_widths=(6,),
        density=0.05,
        chunk_words=32,
        repeats=1,
    )

    assert {row["code_profile"] for row in rows} == {
        "bch_255_239_r16",
        "ebch_256_239_r17",
    }
    assert {row["matrix_shape"] for row in rows} == {"255x16", "256x17"}
    assert {row["packed_word_bits"] for row in rows} == {16, 32}


def test_long_stream_cache_width_summary_compares_l2_l3_against_l1() -> None:
    rows = [
        _row(block_width=8, cache_level="L1", latency=10.0),
        _row(block_width=12, cache_level="L2", latency=7.0),
        _row(block_width=16, cache_level="L3", latency=9.0),
    ]

    summary = summarize_long_stream_cache_width_rows(rows)

    assert len(summary) == 1
    row = summary[0]
    assert row["best_block_width"] == 12
    assert row["best_cache_level"] == "L2"
    assert row["best_l1_block_width"] == 8
    assert row["best_l2_block_width"] == 12
    assert row["l2_better_than_l1"] is True
    assert row["l2_at_least_20pct_faster_than_l1"] is True
    assert row["l2_stable_cv"] is True
    assert row["l2_strong_20x_claim"] is False
    assert row["best_l2_l3_block_width"] == 12
    assert row["l2_l3_better_than_l1"] is True
    assert math.isclose(row["best_l2_l3_over_best_l1"], 0.7)
    assert row["correctness_all_true"] is True


def test_long_stream_cache_width_summary_requires_20x_stable_gap_for_l3_claim() -> None:
    rows = [
        _row(
            block_width=8,
            cache_level="L1",
            latency=10.0,
            total_bits=1_342_177_280,
            latency_cv=0.02,
        ),
        _row(
            block_width=12,
            cache_level="L2",
            latency=9.0,
            total_bits=1_342_177_280,
            latency_cv=0.02,
        ),
        _row(
            block_width=16,
            cache_level="L3",
            latency=7.9,
            total_bits=1_342_177_280,
            latency_cv=0.02,
        ),
    ]

    summary = summarize_long_stream_cache_width_rows(rows)

    assert len(summary) == 1
    row = summary[0]
    assert row["is_20x_long_stream"] is True
    assert row["l3_at_least_20pct_faster_than_l1"] is True
    assert row["l3_stable_cv"] is True
    assert row["l3_strong_20x_claim"] is True
    assert row["l2_strong_20x_claim"] is False


def test_round09_plot_reads_long_stream_cache_width_csv(tmp_path: Path) -> None:
    raw_path = tmp_path / "long_stream_cache_width.csv"
    summary_path = tmp_path / "long_stream_cache_width_summary.csv"
    figure_dir = tmp_path / "figures"
    rows = [
        _row(block_width=8, cache_level="L1", latency=10.0),
        _row(block_width=12, cache_level="L2", latency=7.0),
    ]
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LONG_STREAM_CACHE_WIDTH_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize_long_stream_cache_width_rows(rows)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)

    plot_long_stream_cache_width(
        raw_path=raw_path,
        summary_path=summary_path,
        figure_dir=figure_dir,
    )

    assert (figure_dir / "experiment_round09_long_stream_cache_width.png").exists()
    assert (figure_dir / "experiment_round09_long_stream_cache_width.pdf").exists()


def _row(
    *,
    block_width: int,
    cache_level: str,
    latency: float,
    total_bits: int = 4096,
    latency_cv: float = 0.01,
) -> dict[str, str]:
    fits_l1 = cache_level == "L1"
    fits_l2 = cache_level in {"L1", "L2"}
    fits_l3 = cache_level in {"L1", "L2", "L3"}
    return {
        "preset": "unit",
        "code_profile": "bch_255_239_r16",
        "matrix_kind": "bch_candidate",
        "verification_status": "verified_candidate",
        "matrix_source": "galois_systematic_candidate",
        "matrix_shape": "255x16",
        "component_n": "255",
        "output_r": "16",
        "total_bits": str(total_bits),
        "num_words": str(max(1, total_bits // 255)),
        "chunk_words": "16",
        "iterations": "1",
        "density": "0.05",
        "block_width": str(block_width),
        "packed_word_bits": "16",
        "lut_bytes": str(block_width * 1000),
        "fits_l1": str(fits_l1),
        "fits_l2": str(fits_l2),
        "fits_l3": str(fits_l3),
        "cache_level": cache_level,
        "latency_per_word_us": str(latency),
        "latency_per_word_std_us": "0.01",
        "latency_cv": str(latency_cv),
        "throughput_Mbit_s": "1.0",
        "repeats": "3",
        "mean": "0.001",
        "std": "0.0",
        "correctness_passed": "True",
    }
