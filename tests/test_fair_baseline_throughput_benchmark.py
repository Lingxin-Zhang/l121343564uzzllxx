"""Smoke tests for the fair baseline throughput benchmark."""

from __future__ import annotations

import numpy as np

from benchmarks.bench_fair_baseline_throughput import (
    MatrixSpec,
    run_fair_baseline_rows,
)


def test_fair_baseline_rows_include_absolute_throughput_and_environment() -> None:
    matrix = np.array(
        [
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )

    rows = run_fair_baseline_rows(
        matrix_specs=(MatrixSpec("toy_4_3", matrix, k=2),),
        batch_sizes=(1, 10),
        repeats=1,
        warmups=0,
        block_width=2,
        include_galois=False,
    )

    assert rows
    assert {row["backend"] for row in rows} >= {
        "NaiveGF2Kernel.apply_many",
        "PackedBatchGF2Kernel.apply_many",
        "PackedBlockLUTKernel.apply_many_packed",
    }
    assert {row["task"] for row in rows} == {"syndrome", "parity"}
    assert all(float(row["throughput_Mbit_s"]) > 0.0 for row in rows)
    assert all(float(row["throughput_Mcodeword_s"]) > 0.0 for row in rows)
    assert all(row["cpu_model"] for row in rows)
    assert all(row["numpy_version"] for row in rows)
