"""Tests for cache-aware benchmark metadata fields."""

from __future__ import annotations

from benchmarks.bench_cache_aware import CACHE_AWARE_FIELDNAMES, build_arg_parser, run_cache_aware_rows
from scripts.summarize_results import summarize_cache_aware_rows


REQUIRED_CACHE_FIELDS = {
    "preset",
    "cache_profile",
    "code_profile",
    "matrix_shape",
    "n",
    "r",
    "backend",
    "block_width",
    "batch_size",
    "density",
    "packed_word_bits",
    "packed_dtype",
    "lut_bytes",
    "num_blocks",
    "entries_per_block",
    "fits_l1",
    "fits_l2",
    "fits_l3",
    "l1d_bytes",
    "l2_bytes",
    "l3_bytes",
    "cache_line_bytes",
    "latency_per_word_us",
    "throughput_Mword_s",
    "mean",
    "std",
    "repeats",
    "correctness_passed",
}


def test_cache_aware_fieldnames_include_required_metadata() -> None:
    assert REQUIRED_CACHE_FIELDS <= set(CACHE_AWARE_FIELDNAMES)


def test_cache_aware_cli_cache_override_uses_kb_mb_units() -> None:
    args = build_arg_parser().parse_args(
        ["--l1d-kb", "64", "--l2-kb", "2048", "--l3-mb", "32", "--cache-line", "128"]
    )

    assert args.l1d_kb == 64
    assert args.l2_kb == 2048
    assert args.l3_mb == 32
    assert args.cache_line == 128


def test_cache_aware_rows_include_metadata_for_all_backends() -> None:
    rows = run_cache_aware_rows(
        preset="unit",
        code_profiles=("bch_255_239_r16",),
        block_widths=(4,),
        batch_sizes=(2,),
        densities=(0.05,),
        repeats=1,
        l1d_bytes=64 * 1024,
        l2_bytes=2 * 1024 * 1024,
        l3_bytes=32 * 1024 * 1024,
        cache_line_bytes=128,
    )

    assert rows
    for row in rows:
        assert REQUIRED_CACHE_FIELDS <= set(row)
        assert row["cache_profile"] == "cli_override"
        assert row["matrix_shape"] == "255x16"
        assert row["l1d_bytes"] == 64 * 1024
        assert row["l2_bytes"] == 2 * 1024 * 1024
        assert row["l3_bytes"] == 32 * 1024 * 1024
        assert row["cache_line_bytes"] == 128
        if row["backend"] != "PackedBlockLUT.apply_many_packed":
            assert row["lut_bytes"] == 0
            assert row["num_blocks"] == 0
            assert row["entries_per_block"] == 0
            assert row["fits_l1"] is True


def test_cache_aware_summary_preserves_metadata() -> None:
    rows = [
        {
            "preset": "unit",
            "cache_profile": "cli_override",
            "code_profile": "bch_255_239_r16",
            "matrix_shape": "255x16",
            "n": "255",
            "r": "16",
            "backend": "Naive.apply_many",
            "block_width": "4",
            "batch_size": "2",
            "density": "0.05",
            "packed_word_bits": "16",
            "packed_dtype": "uint16",
            "lut_bytes": "0",
            "num_blocks": "0",
            "entries_per_block": "0",
            "fits_l1": "True",
            "fits_l2": "True",
            "fits_l3": "True",
            "l1d_bytes": "65536",
            "l2_bytes": "2097152",
            "l3_bytes": "33554432",
            "cache_line_bytes": "128",
            "latency_per_word_us": "1.0",
            "throughput_Mword_s": "1.0",
            "mean": "0.000002",
            "std": "0.0",
            "repeats": "1",
            "correctness_passed": "True",
        }
    ]

    summary = summarize_cache_aware_rows(rows)

    assert summary[0]["cache_profile"] == "cli_override"
    assert summary[0]["matrix_shape"] == "255x16"
    assert summary[0]["l1d_bytes"] == 65536
