from pathlib import Path

import pandas as pd


def test_round32_counter_probe_reports_windows_fallback_without_fake_misses():
    from benchmarks.bench_round32_cache_probe import build_cache_probe_rows

    rows = build_cache_probe_rows(
        profiles=("toy",),
        profile_params={"toy": (255, 239, "toy_r16")},
        block_widths=(4, 8),
        batch_sizes=(100, 1000),
        cache_sizes={"l1d_bytes": 32_768, "l2_bytes": 1_048_576, "l3_bytes": 24_000_000},
    )

    assert rows
    assert {row["counter_mode"] for row in rows} == {"cache_fit_fallback"}
    assert all(row["l1_misses_per_bit"] == "" for row in rows)
    assert all(row["llc_misses_per_bit"] == "" for row in rows)
    assert {row["batch_size"] for row in rows} == {100, 1000}


def test_round32_fig2_inset_computes_decode_ratio_from_csv(tmp_path: Path):
    from scripts.plot_round32_fig2_ber_inset import compute_decode_speedup, plot_fig2

    ref = tmp_path / "ref.csv"
    lut = tmp_path / "lut.csv"
    diff = tmp_path / "diff.csv"
    pd.DataFrame(
        {
            "snr_db": [13.5, 13.6],
            "post_fec_ber": [1e-3, 1e-4],
            "post_fec_errors": [100, 80],
            "decode_sec": [10.0, 12.0],
        }
    ).to_csv(ref, index=False)
    pd.DataFrame(
        {
            "snr_db": [13.5, 13.6],
            "post_fec_ber": [1e-3, 1e-4],
            "post_fec_errors": [100, 80],
            "decode_sec": [5.0, 6.0],
        }
    ).to_csv(lut, index=False)
    pd.DataFrame({"snr_db": [13.5, 13.6], "matched": [True, True]}).to_csv(diff, index=False)

    assert compute_decode_speedup(ref, lut)["decode_speedup"] == 2.0
    plot_fig2(ref, lut, diff, tmp_path)
    assert (tmp_path / "round32_fig2_ber_decode_inset.png").exists()
    assert (tmp_path / "round32_fig2_ber_decode_inset.pdf").exists()


def test_round32_fig3_aggregation_and_plot(tmp_path: Path):
    from scripts.plot_round32_fig3_throughput import aggregate_rounds, plot_fig3

    csv_path = tmp_path / "fig3.csv"
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "backend": "PackedBatchGF2Kernel.apply_many",
                "batch_size": 100,
                "throughput_Mbit_s": 10.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "backend": "PackedBatchGF2Kernel.apply_many",
                "batch_size": 100,
                "throughput_Mbit_s": 12.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 1,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "backend": "PackedBlockLUTKernel.apply_many_packed",
                "batch_size": 100,
                "throughput_Mbit_s": 30.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "backend": "PackedBlockLUTKernel.apply_many_packed",
                "batch_size": 100,
                "throughput_Mbit_s": 40.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 1,
            },
        ]
    ).to_csv(csv_path, index=False)

    agg = aggregate_rounds(csv_path)
    lut = agg[agg["backend"].eq("PackedBlockLUTKernel.apply_many_packed")].iloc[0]
    assert lut["throughput_median_Mbit_s"] == 35.0
    assert lut["throughput_min_Mbit_s"] == 30.0
    plot_fig3(csv_path, tmp_path)
    assert (tmp_path / "round32_fig3_throughput.png").exists()
    assert (tmp_path / "round32_fig3_throughput.pdf").exists()


def test_round32_fig4_fallback_plot(tmp_path: Path):
    from scripts.plot_round32_fig4_cache_width import plot_fig4

    width_csv = tmp_path / "width.csv"
    probe_csv = tmp_path / "probe.csv"
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "block_width": 4,
                "throughput_Mbit_s": 100.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
                "theoretical_ops": 1280,
                "cache_level_fit": "L1",
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "block_width": 8,
                "throughput_Mbit_s": 200.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
                "theoretical_ops": 736,
                "cache_level_fit": "L2",
            },
        ]
    ).to_csv(width_csv, index=False)
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "block_width": 4,
                "batch_size": 1000,
                "counter_mode": "cache_fit_fallback",
                "cache_level_fit": "L1",
                "cache_level_ordinal": 1,
            },
            {
                "profile": "bch_255_239_r16",
                "block_width": 8,
                "batch_size": 1000,
                "counter_mode": "cache_fit_fallback",
                "cache_level_fit": "L2",
                "cache_level_ordinal": 2,
            },
        ]
    ).to_csv(probe_csv, index=False)

    plot_fig4(width_csv, probe_csv, tmp_path)
    assert (tmp_path / "round32_fig4_cache_width.png").exists()
    assert (tmp_path / "round32_fig4_cache_width.pdf").exists()
