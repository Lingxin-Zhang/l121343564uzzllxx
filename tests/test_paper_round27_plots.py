"""Smoke tests for Round 27 paper plotting scripts."""

from __future__ import annotations

from pathlib import Path

from scripts import plot_paper_fig2, plot_paper_fig3, plot_paper_fig4


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
