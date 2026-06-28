"""Smoke tests for Round 31 benchmark and plotting helpers."""

from __future__ import annotations

from pathlib import Path

from benchmarks import bench_round31_cache_width
from scripts import plot_round31_fig2_throughput, plot_round31_fig3_cache_width, plot_round31_fig4_ber


def test_round31_lut_bytes_and_prediction_helpers() -> None:
    assert bench_round31_cache_width.lut_table_bytes(239, 16, 8) == 30 * 256 * 2
    assert bench_round31_cache_width.theoretical_ops(239, 16, 4) > bench_round31_cache_width.theoretical_ops(
        239, 16, 24
    )
    prediction = bench_round31_cache_width.predict_cache_widths(239, 16, {"tiny": 16_000})
    assert prediction["tiny"] == 8


def test_round31_fig2_plot_uses_actual_throughput(tmp_path: Path) -> None:
    csv_path = tmp_path / "fig2.csv"
    csv_path.write_text(
        "\n".join(
            [
                "profile,task,backend,batch_size,timed,correctness_passed,throughput_Mbit_s,block_width",
                "bch_255_239_r16,syndrome,PackedBatchGF2Kernel.apply_many,100,True,True,10,",
                "bch_255_239_r16,syndrome,PackedBlockLUTKernel.apply_many_packed,100,True,True,25,12",
                "bch_255_239_r16,parity,PackedBatchGF2Kernel.apply_many,100,True,True,20,",
                "bch_255_239_r16,parity,PackedBlockLUTKernel.apply_many_packed,100,True,True,40,12",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "figures"

    assert plot_round31_fig2_throughput.main(["--csv", str(csv_path), "--output-dir", str(out_dir)]) == 0

    assert (out_dir / "round31_fig2_actual_throughput.png").exists()
    assert (out_dir / "round31_fig2_actual_throughput.pdf").exists()
    assert "Throughput" in plot_round31_fig2_throughput.Y_LABEL
    assert "Speedup" not in plot_round31_fig2_throughput.Y_LABEL


def test_round31_fig3_plot_writes_outputs(tmp_path: Path) -> None:
    csv_path = tmp_path / "fig3.csv"
    rows = [
        "profile,task,backend,block_width,batch_size,timed,correctness_passed,throughput_Mbit_s,ns_per_bit,input_width,output_width,lut_table_bytes,cache_level_fit,theoretical_ops,cv,min_runtime_s,median_runtime_s,max_runtime_s",
        "bch_255_239_r16,syndrome,PackedBlockLUTKernel.apply_many_packed,4,1000,True,True,10,100,255,16,1024,L1,1280,0.01,0.1,0.2,0.3",
        "bch_255_239_r16,syndrome,PackedBlockLUTKernel.apply_many_packed,8,1000,True,True,20,50,255,16,15360,L1,768,0.01,0.1,0.2,0.3",
        "bch_255_231_r24,syndrome,PackedBlockLUTKernel.apply_many_packed,4,1000,True,True,8,125,255,24,1536,L1,1792,0.01,0.1,0.2,0.3",
        "bch_255_231_r24,syndrome,PackedBlockLUTKernel.apply_many_packed,8,1000,True,True,12,80,255,24,24576,L1,1024,0.01,0.1,0.2,0.3",
    ]
    csv_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    out_dir = tmp_path / "figures"

    assert plot_round31_fig3_cache_width.main(["--csv", str(csv_path), "--output-dir", str(out_dir)]) == 0

    assert (out_dir / "round31_fig3_cache_width.png").exists()
    assert (out_dir / "round31_fig3_cache_width.pdf").exists()


def test_round31_fig4_merge_excludes_zero_error_14db(tmp_path: Path) -> None:
    existing_ref = tmp_path / "existing_ref.csv"
    existing_lut = tmp_path / "existing_lut.csv"
    low_ref = tmp_path / "low_ref.csv"
    low_lut = tmp_path / "low_lut.csv"
    diff = tmp_path / "diff.csv"
    header = "snr_db,h,total_bits,post_fec_errors,post_fec_ber,stop_reason,backend\n"
    existing_ref.write_text(
        header
        + "13.75,16,1000,20,0.02,target_errors_reached,syndrome_lut\n"
        + "13.95,16,1000,9,0.009,max_blocks_reached,syndrome_lut\n"
        + "14.0,16,1000,0,0.0,max_blocks_reached,syndrome_lut\n",
        encoding="utf-8",
    )
    existing_lut.write_text(
        header
        + "13.75,16,1000,20,0.02,target_errors_reached,block_lut\n"
        + "13.95,16,1000,9,0.009,max_blocks_reached,block_lut\n"
        + "14.0,16,1000,0,0.0,max_blocks_reached,block_lut\n",
        encoding="utf-8",
    )
    low_ref.write_text(header + "13.5,16,1000,200,0.2,target_errors_reached,syndrome_lut\n", encoding="utf-8")
    low_lut.write_text(header + "13.5,16,1000,200,0.2,target_errors_reached,block_lut\n", encoding="utf-8")
    diff.write_text(
        "snr_db,matched,post_fec_errors_delta,post_fec_ber_delta\n"
        "13.5,True,0,0.0\n13.75,True,0,0.0\n13.95,True,0,0.0\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "figures"
    merged_dir = tmp_path / "raw"

    assert (
        plot_round31_fig4_ber.main(
            [
                "--existing-reference-csv",
                str(existing_ref),
                "--existing-block-lut-csv",
                str(existing_lut),
                "--low-reference-csv",
                str(low_ref),
                "--low-block-lut-csv",
                str(low_lut),
                "--diff-csv",
                str(diff),
                "--output-dir",
                str(out_dir),
                "--merged-output-dir",
                str(merged_dir),
            ]
        )
        == 0
    )

    merged = (merged_dir / "round31_fig4_real_ofec_syndrome_lut_ber.csv").read_text(encoding="utf-8")
    assert "13.5" in merged
    assert "13.75" in merged
    assert "13.95" in merged
    assert "14.0" not in merged
    assert (out_dir / "round31_fig4_real_ofec_ber.png").exists()
    assert (out_dir / "round31_fig4_real_ofec_ber.pdf").exists()
