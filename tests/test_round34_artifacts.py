"""Smoke tests for Round34 benchmark summaries and plotting scripts."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from benchmarks.bench_round34_multicode_syndrome import summarize_rows
from scripts import (
    plot_round34_fig2_ber_overlap,
    plot_round34_fig3_multicode_bars,
    plot_round34_fig3b_decode_time,
)


def test_round34_summary_marks_lut_best_batch() -> None:
    rows = []
    for batch, direct_runtime, lut_runtime in ((100, 0.010, 0.004), (300, 0.030, 0.006)):
        for backend, runtime in (
            ("galois_per_codeword", 0.050),
            ("PackedBatchGF2Kernel.apply_many", direct_runtime),
            ("PackedBlockLUTKernel.apply_many_packed", lut_runtime),
        ):
            for round_index in range(2):
                rows.append(
                    {
                        "profile": "bch_255_239_r16",
                        "task": "syndrome",
                        "backend": backend,
                        "baseline_role": "",
                        "batch_size": batch,
                        "round_index": round_index,
                        "input_width": 255,
                        "output_width": 16,
                        "processed_bits": batch * 255,
                        "block_width": 14 if backend == "PackedBlockLUTKernel.apply_many_packed" else "",
                        "block_width_source": "",
                        "lut_table_bytes": 622592 if backend == "PackedBlockLUTKernel.apply_many_packed" else "",
                        "packed_word_bits": 16,
                        "sample_runtime_s": runtime,
                        "throughput_Mbit_s": batch * 255 / runtime / 1_000_000,
                        "throughput_Mcodeword_s": batch / runtime / 1_000_000,
                        "correctness_passed": True,
                        "timed": True,
                        "skip_reason": "",
                        "exactness_elapsed_s": 0.0,
                        "warmups": 1,
                        "repeats": 2,
                        "build_init_s": 0.0,
                        "elapsed_config_s": 0.0,
                    }
                )

    summary = pd.DataFrame(summarize_rows(rows))
    rep = summary[summary["is_representative_batch"].astype(bool)]

    assert set(rep["batch_size"]) == {300}
    assert len(rep) == 3


def test_round34_fig3_bar_plot_writes_outputs(tmp_path: Path) -> None:
    csv_path = tmp_path / "summary.csv"
    rows = []
    profiles = ["bch_255_239_r16", "bch_255_231_r24", "bch_511_484_r27", "bch_1023_993_r30"]
    backends = [
        ("galois_per_codeword", 4.0),
        ("PackedBatchGF2Kernel.apply_many", 40.0),
        ("PackedBlockLUTKernel.apply_many_packed", 400.0),
    ]
    for idx, profile in enumerate(profiles):
        for backend, base in backends:
            rows.append(
                {
                    "profile": profile,
                    "task": "syndrome",
                    "backend": backend,
                    "baseline_role": "",
                    "batch_size": 1000,
                    "representative_batch_size": 1000,
                    "is_representative_batch": True,
                    "input_width": 255,
                    "output_width": 16,
                    "processed_bits": 255000,
                    "block_width": 14 if "BlockLUT" in backend else "",
                    "block_width_source": "",
                    "lut_table_bytes": 1,
                    "packed_word_bits": 16,
                    "median_runtime_s": 0.001,
                    "min_runtime_s": 0.001,
                    "max_runtime_s": 0.001,
                    "stdev_runtime_s": 0.0,
                    "cv": 0.01,
                    "throughput_Mbit_s": base + idx,
                    "throughput_Mcodeword_s": 1.0,
                    "round_count": 2,
                    "correctness_passed": True,
                    "timed": True,
                    "skip_reason": "",
                    "warmups": 1,
                    "repeats": 2,
                    "build_init_s": 0.0,
                }
            )
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    out_dir = tmp_path / "figures"
    representative = tmp_path / "representative.csv"

    assert (
        plot_round34_fig3_multicode_bars.main(
            ["--csv", str(csv_path), "--output-dir", str(out_dir), "--representative-output", str(representative)]
        )
        == 0
    )

    assert (out_dir / "round34_fig3_multicode_three_backend.png").exists()
    assert (out_dir / "round34_fig3_multicode_three_backend.pdf").exists()
    assert representative.exists()


def test_round34_fig2_and_fig3b_plots_write_outputs(tmp_path: Path) -> None:
    ref = tmp_path / "ref.csv"
    lut = tmp_path / "lut.csv"
    diff = tmp_path / "diff.csv"
    pd.DataFrame(
        {
            "snr_db": [13.5, 13.6, 13.7],
            "post_fec_ber": [1e-2, 5e-3, 1e-3],
            "decode_sec": [10.0, 11.0, 12.0],
            "elapsed_sec": [20.0, 21.0, 22.0],
            "backend": ["syndrome_lut"] * 3,
        }
    ).to_csv(ref, index=False)
    pd.DataFrame(
        {
            "snr_db": [13.5, 13.6, 13.7],
            "post_fec_ber": [1e-2, 5e-3, 1e-3],
            "decode_sec": [8.0, 9.0, 10.0],
            "elapsed_sec": [18.0, 19.0, 20.0],
            "backend": ["block_lut"] * 3,
        }
    ).to_csv(lut, index=False)
    pd.DataFrame(
        {
            "snr_db": [13.5, 13.6, 13.7],
            "matched": [True, True, True],
            "post_fec_errors_delta": [0, 0, 0],
            "post_fec_ber_delta": [0.0, 0.0, 0.0],
        }
    ).to_csv(diff, index=False)
    out_dir = tmp_path / "figures"
    timing_summary = tmp_path / "timing.csv"

    assert (
        plot_round34_fig2_ber_overlap.main(
            ["--reference-csv", str(ref), "--block-lut-csv", str(lut), "--diff-csv", str(diff), "--output-dir", str(out_dir)]
        )
        == 0
    )
    assert (
        plot_round34_fig3b_decode_time.main(
            [
                "--reference-csv",
                str(ref),
                "--block-lut-csv",
                str(lut),
                "--output-dir",
                str(out_dir),
                "--summary-output",
                str(timing_summary),
            ]
        )
        == 0
    )

    assert (out_dir / "round34_fig2_real_ofec_ber_overlap.png").exists()
    assert (out_dir / "round34_fig2_real_ofec_ber_overlap.pdf").exists()
    assert (out_dir / "round34_fig3b_decode_time.png").exists()
    assert (out_dir / "round34_fig3b_decode_time.pdf").exists()
    assert timing_summary.exists()
