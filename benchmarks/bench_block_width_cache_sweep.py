"""Block-width/cache sweep for packed block-LUT fixed GF(2) maps."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

from benchmarks._common import RAW_DIR, ensure_result_dirs, write_csv
from benchmarks.bench_fixed_map_three_backend import (
    BackendSpec,
    DEFAULT_MAX_GALOIS_BATCH_SIZE,
    DEFAULT_MAX_IN_MEMORY_ROWS,
    DEFAULT_MAX_TIMED_BATCH_SIZE,
    DEFAULT_REPEATS,
    DEFAULT_WARMUPS,
    MatrixSpec,
    _as_gf2_matrix,
    _galois_encode_parity_per_codeword,
    _galois_matrix_apply_per_codeword,
    _parse_int_list,
    _row_for_backend,
    default_matrix_specs,
    environment_fields,
)
from linear_kernel import PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.cache_profile import get_cache_profile

DEFAULT_BATCH_SIZES = (100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000)
DEFAULT_BLOCK_WIDTHS = (8, 10, 11, 12, 13, 14, 16, 18, 20)
RNG_SEED = 20260730

FIELDNAMES = [
    "profile",
    "task",
    "block_width",
    "lut_table_bytes",
    "cache_level_fit",
    "theoretical_a32_lut_table_bytes",
    "theoretical_a32_cache_level_fit",
    "batch_size",
    "backend",
    "baseline_role",
    "input_width",
    "output_width",
    "processed_bits",
    "packed_word_bits",
    "chunked_online",
    "chunk_size",
    "build_init_s",
    "exactness_elapsed_s",
    "timing_elapsed_s",
    "elapsed_s",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "median_runtime_s",
    "min_runtime_s",
    "max_runtime_s",
    "cv",
    "samples_s",
    "warmups",
    "repeats",
    "correctness_passed",
    "timed",
    "galois_available",
    "galois_version",
    "cpu_model",
    "l1d_bytes",
    "l2_bytes",
    "l3_bytes",
    "python_version",
    "numpy_version",
    "thread_count",
    "seed",
    "notes",
]


def lut_table_bytes(input_width: int, output_width: int, block_width: int) -> int:
    blocks = math.ceil(int(input_width) / int(block_width))
    entry_bytes = math.ceil(int(output_width) / 8)
    return int(blocks * (1 << int(block_width)) * entry_bytes)


def cache_level_fit(byte_count: int) -> str:
    cache = get_cache_profile()
    if int(byte_count) <= cache.l1d_bytes:
        return "L1"
    if int(byte_count) <= cache.l2_bytes:
        return "L2"
    if int(byte_count) <= cache.l3_bytes:
        return "L3"
    return "DRAM"


def _reference_backends(
    *,
    spec: MatrixSpec,
    task: str,
    matrix: Any,
    include_galois: bool,
    max_galois_batch_size: int,
) -> list[BackendSpec]:
    packed_batch = PackedBatchGF2Kernel(matrix)
    backends = [
        BackendSpec(
            "PackedBatchGF2Kernel.apply_many",
            "fair vectorized same-task baseline",
            "unpacked",
            packed_batch.apply_many,
            "reference line shared by all block widths",
        )
    ]
    if include_galois:
        if task == "parity":
            fn = lambda x, spec=spec: _galois_encode_parity_per_codeword(x, spec)
            notes = "naive library-call baseline, per-codeword bch.encode"
        else:
            fn = lambda x, matrix=matrix: _galois_matrix_apply_per_codeword(x, matrix)
            notes = "naive library-call baseline, per-codeword galois GF(2) matmul"
        backends.append(
            BackendSpec(
                "galois_per_codeword",
                "naive library-call baseline, per-codeword",
                "unpacked",
                fn,
                notes,
                max_batch_size=max_galois_batch_size,
            )
        )
    return backends


def _lut_backend(matrix: Any, block_width: int) -> BackendSpec:
    packed_word_bits = 16 if matrix.shape[1] <= 16 else 32
    kernel = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=packed_word_bits)
    return BackendSpec(
        "PackedBlockLUTKernel.apply_many_packed",
        "packed block-LUT kernel under test",
        "packed",
        kernel.apply_many_packed,
        "block-width sweep row",
    )


def _decorate(row: dict[str, Any], input_width: int, output_width: int, block_width: int | str) -> dict[str, Any]:
    if isinstance(block_width, int):
        bytes_value = lut_table_bytes(input_width, output_width, block_width)
        level = cache_level_fit(bytes_value)
    else:
        bytes_value = ""
        level = ""
    theoretical_bytes = lut_table_bytes(input_width, output_width, 32)
    row = dict(row)
    row.update(
        {
            "block_width": block_width,
            "lut_table_bytes": bytes_value,
            "cache_level_fit": level,
            "theoretical_a32_lut_table_bytes": theoretical_bytes,
            "theoretical_a32_cache_level_fit": cache_level_fit(theoretical_bytes),
        }
    )
    return {field: row.get(field, "") for field in FIELDNAMES}


def run_block_width_cache_sweep_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    block_widths: tuple[int, ...] = DEFAULT_BLOCK_WIDTHS,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    include_galois: bool = True,
    max_in_memory_rows: int = DEFAULT_MAX_IN_MEMORY_ROWS,
    max_timed_batch_size: int | None = DEFAULT_MAX_TIMED_BATCH_SIZE,
    max_galois_batch_size: int = DEFAULT_MAX_GALOIS_BATCH_SIZE,
    seed: int = RNG_SEED,
) -> list[dict[str, Any]]:
    env = environment_fields()
    include_galois = bool(include_galois and env["galois_available"])
    import numpy as np

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for raw_spec in matrix_specs or default_matrix_specs():
        matrix = _as_gf2_matrix(raw_spec.matrix)
        spec = MatrixSpec(raw_spec.profile, matrix, int(raw_spec.k), float(raw_spec.init_elapsed_s), raw_spec.bch)
        for task, task_matrix in (("parity", matrix[: spec.k]), ("syndrome", matrix)):
            input_width, output_width = task_matrix.shape
            for batch_size in batch_sizes:
                for backend in _reference_backends(
                    spec=spec,
                    task=task,
                    matrix=task_matrix,
                    include_galois=include_galois,
                    max_galois_batch_size=max_galois_batch_size,
                ):
                    row = _row_for_backend(
                        spec=spec,
                        task=task,
                        backend=backend,
                        matrix=task_matrix,
                        batch_size=int(batch_size),
                        block_width=0,
                        warmups=warmups,
                        repeats=repeats,
                        max_in_memory_rows=max_in_memory_rows,
                        max_timed_batch_size=max_timed_batch_size,
                        rng=rng,
                        env=env,
                        seed=seed,
                    )
                    rows.append(_decorate(row, input_width, output_width, "reference"))
                for block_width in block_widths:
                    backend = _lut_backend(task_matrix, int(block_width))
                    row = _row_for_backend(
                        spec=spec,
                        task=task,
                        backend=backend,
                        matrix=task_matrix,
                        batch_size=int(batch_size),
                        block_width=int(block_width),
                        warmups=warmups,
                        repeats=repeats,
                        max_in_memory_rows=max_in_memory_rows,
                        max_timed_batch_size=max_timed_batch_size,
                        rng=rng,
                        env=env,
                        seed=seed,
                    )
                    rows.append(_decorate(row, input_width, output_width, int(block_width)))
    return rows


def _write_or_append_csv(output: Path, rows: list[dict[str, Any]], append: bool) -> None:
    if append and output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            rows = [*list(csv.DictReader(f)), *rows]
    write_csv(output, rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run block-width/cache sweep for fixed GF(2) maps.")
    parser.add_argument("--batch-sizes", default=",".join(str(value) for value in DEFAULT_BATCH_SIZES))
    parser.add_argument("--block-widths", default=",".join(str(value) for value in DEFAULT_BLOCK_WIDTHS))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--max-timed-batch-size", type=int, default=DEFAULT_MAX_TIMED_BATCH_SIZE)
    parser.add_argument("--max-galois-batch-size", type=int, default=DEFAULT_MAX_GALOIS_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--skip-galois", action="store_true")
    parser.add_argument("--output", type=Path, default=RAW_DIR / "block_width_cache_sweep.csv")
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_block_width_cache_sweep_rows(
        batch_sizes=_parse_int_list(args.batch_sizes),
        block_widths=_parse_int_list(args.block_widths),
        repeats=args.repeats,
        warmups=args.warmups,
        include_galois=not args.skip_galois,
        max_in_memory_rows=args.max_in_memory_rows,
        max_timed_batch_size=args.max_timed_batch_size,
        max_galois_batch_size=args.max_galois_batch_size,
        seed=args.seed,
    )
    _write_or_append_csv(args.output, rows, args.append)
    print(f"wrote {args.output}")
    failed = [row for row in rows if row["correctness_passed"] is not True]
    if failed:
        print(f"WARNING: {len(failed)} rows failed exactness and were not timed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
