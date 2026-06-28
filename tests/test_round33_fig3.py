from pathlib import Path

import numpy as np
import pandas as pd

from linear_kernel import PackedBlockLUTKernel


def test_staged_block_lut_matches_kernel_and_reports_stage_times():
    from benchmarks.bench_round33_fig3_dense_batch import staged_apply_many_packed

    matrix = np.array(
        [
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )
    x_batch = np.array(
        [
            [1, 0, 1, 0],
            [0, 1, 1, 1],
            [1, 1, 0, 0],
        ],
        dtype=np.uint8,
    )
    kernel = PackedBlockLUTKernel(matrix, block_width=2, packed_word_bits=16)

    staged, stage_times = staged_apply_many_packed(kernel, x_batch)

    assert np.array_equal(staged, kernel.apply_many_packed(x_batch))
    assert set(stage_times) == {
        "stage_read_prepare_s",
        "stage_index_s",
        "stage_lookup_s",
        "stage_xor_s",
        "stage_write_s",
    }
    assert all(value >= 0.0 for value in stage_times.values())


def test_streaming_chunk_plan_counts_all_words():
    from benchmarks.bench_round33_fig3_dense_batch import make_stream_chunks

    chunks = make_stream_chunks(total_rows=2500, chunk_rows=1000)

    assert chunks == (1000, 1000, 500)
    assert sum(chunks) == 2500


def test_incremental_csv_writer_flushes_completed_rows(tmp_path: Path):
    from benchmarks.bench_round33_fig3_dense_batch import IncrementalCsvWriter

    csv_path = tmp_path / "rows.csv"
    writer = IncrementalCsvWriter(csv_path)

    writer.write({"batch_size": 10, "throughput_Mbit_s": 1.0})
    observed = pd.read_csv(csv_path)
    writer.close()

    assert observed.to_dict("records") == [{"batch_size": 10, "throughput_Mbit_s": 1.0}]


def test_incremental_csv_writer_can_create_empty_file(tmp_path: Path):
    from benchmarks.bench_round33_fig3_dense_batch import IncrementalCsvWriter

    csv_path = tmp_path / "empty.csv"
    writer = IncrementalCsvWriter(csv_path)
    writer.ensure_exists()

    assert csv_path.exists()
    assert csv_path.read_text(encoding="utf-8") == ""


def test_round33_summary_identifies_bulk_and_streaming_speedups(tmp_path: Path):
    from scripts.plot_round33_fig3_dense_batch import summarize_speedups

    csv_path = tmp_path / "throughput.csv"
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "bulk",
                "batch_size": 1000,
                "backend": "PackedBatchGF2Kernel.apply_many",
                "throughput_Mbit_s": 50.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "bulk",
                "batch_size": 1000,
                "backend": "PackedBlockLUTKernel.apply_many_packed",
                "throughput_Mbit_s": 500.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "stream_chunked",
                "batch_size": 1_000_000,
                "backend": "PackedBatchGF2Kernel.apply_many",
                "throughput_Mbit_s": 40.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "stream_chunked",
                "batch_size": 1_000_000,
                "backend": "PackedBlockLUTKernel.apply_many_packed",
                "throughput_Mbit_s": 400.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
        ]
    ).to_csv(csv_path, index=False)

    summary = summarize_speedups(csv_path)

    bulk = summary[(summary["task"] == "syndrome") & (summary["mode"] == "bulk")].iloc[0]
    stream = summary[(summary["task"] == "syndrome") & (summary["mode"] == "stream_chunked")].iloc[0]
    assert bulk["lut_vs_direct_median"] == 10.0
    assert stream["lut_vs_direct_median"] == 10.0


def test_round33_plot_writes_main_and_stage_figures(tmp_path: Path):
    from scripts.plot_round33_fig3_dense_batch import plot_all

    throughput = tmp_path / "throughput.csv"
    stages = tmp_path / "stages.csv"
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "bulk",
                "batch_size": 100,
                "backend": "PackedBatchGF2Kernel.apply_many",
                "throughput_Mbit_s": 10.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "mode": "bulk",
                "batch_size": 100,
                "backend": "PackedBlockLUTKernel.apply_many_packed",
                "throughput_Mbit_s": 30.0,
                "timed": True,
                "correctness_passed": True,
                "round_index": 0,
            },
        ]
    ).to_csv(throughput, index=False)
    pd.DataFrame(
        [
            {
                "profile": "bch_255_239_r16",
                "task": "syndrome",
                "batch_size": 100,
                "round_index": 0,
                "stage_read_prepare_pct": 20.0,
                "stage_index_pct": 30.0,
                "stage_lookup_pct": 15.0,
                "stage_xor_pct": 25.0,
                "stage_write_pct": 10.0,
            }
        ]
    ).to_csv(stages, index=False)

    plot_all(throughput, stages, tmp_path)

    assert (tmp_path / "round33_fig3_dense_batch.png").exists()
    assert (tmp_path / "round33_fig3_stage_breakdown.png").exists()
    assert (tmp_path / "round33_fig3_scatter.png").exists()
