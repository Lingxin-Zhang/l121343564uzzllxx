"""Smoke tests for Round 27 paper plotting scripts."""

from __future__ import annotations

from pathlib import Path

from scripts import (
    plot_paper_fig2,
    plot_paper_fig3,
    plot_paper_fig4,
    plot_round30_real_ofec_ber,
)


def test_backend_display_labels_are_neutral() -> None:
    forbidden = ("galois", "AFF3CT", "aff3ct")
    for label in plot_paper_fig2.DISPLAY_BACKEND.values():
        assert all(token not in label for token in forbidden)
    assert plot_paper_fig2.DISPLAY_BACKEND["PackedBatchGF2Kernel.apply_many"] == (
        "direct vectorized GF(2) matmul"
    )
    assert plot_paper_fig2.DISPLAY_BACKEND["PackedBlockLUTKernel.apply_many_packed"] == (
        "block-LUT (cache-aware)"
    )
    assert plot_paper_fig2.DISPLAY_BACKEND["galois_per_codeword"] == "naive per-codeword"


def test_round27_plot_scripts_write_png_and_pdf(tmp_path: Path) -> None:
    figure_dir = tmp_path / "figures"

    assert plot_paper_fig2.main(["--output-dir", str(figure_dir)]) == 0
    assert plot_paper_fig3.main(["--output-dir", str(figure_dir)]) == 0
    assert plot_paper_fig4.main(["--output-dir", str(figure_dir)]) == 0

    for stem in (
        "fig2_fixed_map_speedup",
        "fig3_block_width_cache_sweep",
        "fig4_decode_syndrome_accel",
    ):
        assert (figure_dir / f"{stem}.png").exists()
        assert (figure_dir / f"{stem}.pdf").exists()


def test_round30_real_ofec_plot_writes_png_and_pdf(tmp_path: Path) -> None:
    figure_dir = tmp_path / "figures"

    assert plot_round30_real_ofec_ber.main(["--output-dir", str(figure_dir)]) == 0

    assert (figure_dir / "round30_real_ofec_ber.png").exists()
    assert (figure_dir / "round30_real_ofec_ber.pdf").exists()
    assert plot_round30_real_ofec_ber.load_curve_match_count(
        plot_round30_real_ofec_ber.DEFAULT_DIFF_CSV
    ) == 10


def test_round30_real_ofec_plot_accepts_custom_stem_and_inputs(tmp_path: Path) -> None:
    reference_csv = tmp_path / "reference.csv"
    block_lut_csv = tmp_path / "block_lut.csv"
    diff_csv = tmp_path / "diff.csv"
    figure_dir = tmp_path / "figures"
    header = (
        "snr_db,h,post_fec_ber,stop_reason,total_blocks,emitted_blocks,total_bits,"
        "pre_fec_errors,post_fec_errors\n"
    )
    row = "14.0,18,1e-8,max_blocks_reached,50000,49800,203980800,100,0\n"
    reference_csv.write_text(header + row, encoding="utf-8")
    block_lut_csv.write_text(header + row, encoding="utf-8")
    diff_csv.write_text(
        "snr_db,matched,total_blocks_delta,emitted_blocks_delta,total_bits_delta,"
        "pre_fec_errors_delta,post_fec_errors_delta,pre_fec_ber_delta,post_fec_ber_delta\n"
        "14.0,True,0,0,0,0,0,0.0,0.0\n",
        encoding="utf-8",
    )

    assert (
        plot_round30_real_ofec_ber.main(
            [
                "--reference-csv",
                str(reference_csv),
                "--block-lut-csv",
                str(block_lut_csv),
                "--diff-csv",
                str(diff_csv),
                "--output-dir",
                str(figure_dir),
                "--output-stem",
                "round30_h18_core",
            ]
        )
        == 0
    )

    assert (figure_dir / "round30_h18_core.png").exists()
    assert (figure_dir / "round30_h18_core.pdf").exists()


def test_round30_real_ofec_curve_displays_zero_error_as_upper_bound() -> None:
    snr, ber, stop, zero_error = plot_round30_real_ofec_ber._curve(
        [
            {
                "snr_db": "14.0",
                "post_fec_ber": "0.0",
                "post_fec_errors": "0",
                "total_bits": "1000000",
                "stop_reason": "max_blocks_reached",
            }
        ]
    )

    assert snr == [14.0]
    assert 0.0 < ber[0] < 1e-5
    assert stop == ["max_blocks_reached"]
    assert zero_error == [True]


def test_fig3_uses_block_width_w_label() -> None:
    assert "Block width w" in plot_paper_fig3.BLOCK_WIDTH_LABEL


def test_fig2_speedup_data_uses_timed_rows_and_keeps_batch_one() -> None:
    rows = plot_paper_fig2.load_fig2_points(plot_paper_fig2.DEFAULT_CSV)
    syndrome_lut = [
        row
        for row in rows
        if row["task"] == "syndrome" and row["backend"] == "PackedBlockLUTKernel.apply_many_packed"
    ]

    assert any(row["batch_size"] == 1 for row in syndrome_lut)
    assert all(row["timed"] is True for row in rows)
    assert all("speedup_vs_direct" in row for row in syndrome_lut)
