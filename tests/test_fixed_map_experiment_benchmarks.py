"""Smoke tests for fixed-map experiment benchmarks."""

from __future__ import annotations

import numpy as np

from benchmarks.bench_block_width_cache_sweep import run_block_width_cache_sweep_rows
from benchmarks.bench_decode_syndrome_accel import run_decode_syndrome_accel_rows
from benchmarks.bench_fixed_map_three_backend import MatrixSpec, run_three_backend_rows


def _toy_spec() -> MatrixSpec:
    matrix = np.array(
        [
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )
    return MatrixSpec(profile="toy_4_2_r3", matrix=matrix, k=2, init_elapsed_s=0.0)


def test_three_backend_rows_emit_exact_timed_rows() -> None:
    rows = run_three_backend_rows(
        matrix_specs=(_toy_spec(),),
        batch_sizes=(1, 4),
        long_batch_sizes=(),
        repeats=1,
        warmups=0,
        block_widths_by_task={("toy_4_2_r3", "parity"): 2, ("toy_4_2_r3", "syndrome"): 2},
        include_galois=False,
        max_in_memory_rows=8,
    )

    assert rows
    assert {row["task"] for row in rows} == {"parity", "syndrome"}
    assert {row["backend"] for row in rows} >= {
        "PackedBatchGF2Kernel.apply_many",
        "PackedBlockLUTKernel.apply_many_packed",
    }
    assert all(row["correctness_passed"] is True for row in rows)
    assert all(float(row["throughput_Mbit_s"]) > 0.0 for row in rows)
    assert all("elapsed_s" in row for row in rows)
    assert all("build_init_s" in row for row in rows)


def test_block_width_cache_sweep_rows_record_cache_fit_and_references() -> None:
    rows = run_block_width_cache_sweep_rows(
        matrix_specs=(_toy_spec(),),
        batch_sizes=(4,),
        block_widths=(1, 2),
        repeats=1,
        warmups=0,
        include_galois=False,
        max_in_memory_rows=8,
    )

    assert rows
    assert {row["backend"] for row in rows} >= {
        "PackedBlockLUTKernel.apply_many_packed",
        "PackedBatchGF2Kernel.apply_many",
    }
    lut_rows = [row for row in rows if row["backend"] == "PackedBlockLUTKernel.apply_many_packed"]
    assert {row["block_width"] for row in lut_rows} == {1, 2}
    assert all(int(row["lut_table_bytes"]) > 0 for row in lut_rows)
    assert all(row["cache_level_fit"] in {"L1", "L2", "L3", "DRAM"} for row in lut_rows)
    assert all(int(row["theoretical_a32_lut_table_bytes"]) > 0 for row in rows)


def test_decode_syndrome_accel_rows_keep_decisions_identical() -> None:
    rows = run_decode_syndrome_accel_rows(
        matrix_specs=(_toy_spec(),),
        batch_sizes=(4,),
        repeats=1,
        warmups=0,
        block_width=2,
        t=1,
    )

    assert rows
    assert {row["backend"] for row in rows} == {
        "NaiveGF2Kernel.apply_many",
        "PackedBlockLUTKernel.apply_many_packed",
    }
    assert all(row["correctness_passed"] is True for row in rows)
    assert all(int(row["decision_mismatch_count"]) == 0 for row in rows)
    assert all(int(row["status_mismatch_count"]) == 0 for row in rows)
