"""Round 31 cache-width benchmark helpers and CLI.

This runner is intentionally layered on top of the existing fixed-map kernels.
It adds Round 31 reporting fields: ns/bit, explicit measurement placement,
cache-width predictions, affinity/frequency-lock status, and safe skipping for
LUTs that would exceed a configured memory budget.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, write_csv
from benchmarks.bench_block_width_cache_sweep import cache_level_fit
from benchmarks.bench_fixed_map_three_backend import (
    MatrixSpec,
    _as_gf2_matrix,
    _make_chunks,
    _parse_int_list,
    _random_batch,
    build_systematic_bch_matrix,
    environment_fields,
    pack_batch,
)
from linear_kernel import NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.cache_profile import get_cache_profile

DEFAULT_PROFILES = ("255_239", "255_231", "511_484", "1023_993")
DEFAULT_BATCH_SIZES = (100, 1_000, 10_000, 100_000, 300_000)
DEFAULT_BLOCK_WIDTHS = tuple(range(4, 25))
DEFAULT_REPEATS = 15
DEFAULT_WARMUPS = 30
DEFAULT_MAX_IN_MEMORY_ROWS = 300_000
DEFAULT_MAX_LUT_TABLE_BYTES = 768 * 1024 * 1024
RNG_SEED = 42

PROFILE_PARAMS = {
    "255_239": (255, 239, "bch_255_239_r16"),
    "255_231": (255, 231, "bch_255_231_r24"),
    "511_484": (511, 484, "bch_511_484_r27"),
    "1023_993": (1023, 993, "bch_1023_993_r30"),
}

FIELDNAMES = [
    "profile",
    "task",
    "measurement_mode",
    "block_width",
    "batch_size",
    "input_width",
    "output_width",
    "lut_table_bytes",
    "cache_level_fit",
    "theoretical_ops",
    "theoretical_continuous_ops",
    "predicted_l1_w",
    "predicted_l2_w",
    "predicted_l3_w",
    "backend",
    "processed_bits",
    "packed_word_bits",
    "build_init_s",
    "kernel_build_s",
    "exactness_elapsed_s",
    "timing_elapsed_s",
    "elapsed_s",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "ns_per_bit",
    "median_runtime_s",
    "min_runtime_s",
    "max_runtime_s",
    "stdev_runtime_s",
    "cv",
    "samples_s",
    "warmups",
    "repeats",
    "correctness_passed",
    "timed",
    "skip_reason",
    "affinity_status",
    "frequency_lock_status",
    "cache_flush_bytes",
    "measurement_order",
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


def theoretical_ops(input_width: int, output_width: int, block_width: int) -> int:
    return int((int(block_width) + int(output_width)) * math.ceil(int(input_width) / int(block_width)))


def theoretical_continuous_ops(input_width: int, output_width: int, block_width: int) -> float:
    return float((int(block_width) + int(output_width)) * (float(input_width) / float(block_width)))


def predict_cache_widths(
    input_width: int,
    output_width: int,
    cache_bytes_by_level: dict[str, int] | None = None,
    *,
    widths: tuple[int, ...] = DEFAULT_BLOCK_WIDTHS,
) -> dict[str, int]:
    if cache_bytes_by_level is None:
        cache = get_cache_profile()
        cache_bytes_by_level = {"L1": cache.l1d_bytes, "L2": cache.l2_bytes, "L3": cache.l3_bytes}
    predictions: dict[str, int] = {}
    for level, capacity in cache_bytes_by_level.items():
        fitting = [w for w in widths if lut_table_bytes(input_width, output_width, w) <= int(capacity)]
        predictions[level] = max(fitting) if fitting else min(widths)
    return predictions


def _summary(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "median_runtime_s": 0.0,
            "min_runtime_s": 0.0,
            "max_runtime_s": 0.0,
            "stdev_runtime_s": 0.0,
            "cv": 0.0,
        }
    mean = statistics.fmean(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "median_runtime_s": statistics.median(samples),
        "min_runtime_s": min(samples),
        "max_runtime_s": max(samples),
        "stdev_runtime_s": std,
        "cv": (std / mean) if mean > 0 else 0.0,
    }


def _try_set_affinity(cpu_core: int | None) -> str:
    if cpu_core is None:
        return "not requested"
    try:
        import psutil

        process = psutil.Process()
        before = process.cpu_affinity()
        if int(cpu_core) not in before:
            return f"requested core {cpu_core} not in current affinity {before}"
        process.cpu_affinity([int(cpu_core)])
        return f"psutil cpu_affinity set to {cpu_core}"
    except Exception as exc:  # pragma: no cover - platform dependent
        return f"affinity unavailable: {type(exc).__name__}: {exc}"


def _frequency_lock_status() -> str:
    if os.name == "nt":
        return "cpupower/intel_pstate unavailable on Windows"
    no_turbo = Path("/sys/devices/system/cpu/intel_pstate/no_turbo")
    if not no_turbo.exists():
        return "intel_pstate no_turbo unavailable; not locked"
    return "frequency lock not attempted by benchmark process"


def build_round31_matrix_specs(profile_keys: tuple[str, ...] = DEFAULT_PROFILES) -> tuple[MatrixSpec, ...]:
    specs = []
    for key in profile_keys:
        if key not in PROFILE_PARAMS:
            raise ValueError(f"unknown Round 31 profile key: {key}")
        n, k, profile = PROFILE_PARAMS[key]
        specs.append(build_systematic_bch_matrix(n, k, profile=profile))
    return tuple(specs)


def _touch_cache_flush(cache_flush: np.ndarray | None) -> None:
    if cache_flush is None or cache_flush.size == 0:
        return
    # One vectorized sum touches the buffer without allocating another large array.
    int(cache_flush.sum(dtype=np.uint64))


def _time_samples(fn, *, warmups: int, repeats: int) -> list[float]:
    for _ in range(int(warmups)):
        fn()
    samples = []
    for _ in range(int(repeats)):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _make_stream_fn(fn, chunks: tuple[np.ndarray, ...], cache_flush: np.ndarray | None):
    def apply_stream() -> np.ndarray:
        last = np.array([], dtype=np.uint32)
        for chunk in chunks:
            _touch_cache_flush(cache_flush)
            last = fn(chunk)
        return last

    return apply_stream


def _empty_row(
    *,
    spec: MatrixSpec,
    task: str,
    measurement_mode: str,
    block_width: int,
    batch_size: int,
    input_width: int,
    output_width: int,
    env: dict[str, Any],
    seed: int,
    warmups: int,
    repeats: int,
    affinity_status: str,
    frequency_lock_status: str,
    cache_flush_bytes: int,
    skip_reason: str,
) -> dict[str, Any]:
    predictions = predict_cache_widths(input_width, output_width)
    lut_bytes = lut_table_bytes(input_width, output_width, block_width)
    row = {
        "profile": spec.profile,
        "task": task,
        "measurement_mode": measurement_mode,
        "block_width": int(block_width),
        "batch_size": int(batch_size),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "lut_table_bytes": lut_bytes,
        "cache_level_fit": cache_level_fit(lut_bytes),
        "theoretical_ops": theoretical_ops(input_width, output_width, block_width),
        "theoretical_continuous_ops": theoretical_continuous_ops(input_width, output_width, block_width),
        "predicted_l1_w": predictions["L1"],
        "predicted_l2_w": predictions["L2"],
        "predicted_l3_w": predictions["L3"],
        "backend": "PackedBlockLUTKernel.apply_many_packed",
        "processed_bits": int(batch_size) * int(input_width),
        "packed_word_bits": 16 if output_width <= 16 else 32,
        "build_init_s": float(spec.init_elapsed_s),
        "kernel_build_s": 0.0,
        "exactness_elapsed_s": 0.0,
        "timing_elapsed_s": 0.0,
        "elapsed_s": 0.0,
        "throughput_Mbit_s": 0.0,
        "throughput_Mcodeword_s": 0.0,
        "ns_per_bit": 0.0,
        "median_runtime_s": 0.0,
        "min_runtime_s": 0.0,
        "max_runtime_s": 0.0,
        "stdev_runtime_s": 0.0,
        "cv": 0.0,
        "samples_s": "",
        "warmups": int(warmups),
        "repeats": int(repeats),
        "correctness_passed": False,
        "timed": False,
        "skip_reason": skip_reason,
        "affinity_status": affinity_status,
        "frequency_lock_status": frequency_lock_status,
        "cache_flush_bytes": int(cache_flush_bytes),
        "measurement_order": "interleaved_by_width",
        **env,
        "seed": int(seed),
        "notes": "",
    }
    return {field: row.get(field, "") for field in FIELDNAMES}


def _bench_one(
    *,
    spec: MatrixSpec,
    task: str,
    matrix: np.ndarray,
    measurement_mode: str,
    block_width: int,
    batch_size: int,
    warmups: int,
    repeats: int,
    max_in_memory_rows: int,
    max_lut_table_bytes: int,
    rng: np.random.Generator,
    env: dict[str, Any],
    seed: int,
    affinity_status: str,
    frequency_lock_status: str,
    cache_flush_bytes: int,
) -> dict[str, Any]:
    input_width, output_width = matrix.shape
    lut_bytes = lut_table_bytes(input_width, output_width, block_width)
    if lut_bytes > int(max_lut_table_bytes):
        return _empty_row(
            spec=spec,
            task=task,
            measurement_mode=measurement_mode,
            block_width=block_width,
            batch_size=batch_size,
            input_width=input_width,
            output_width=output_width,
            env=env,
            seed=seed,
            warmups=warmups,
            repeats=repeats,
            affinity_status=affinity_status,
            frequency_lock_status=frequency_lock_status,
            cache_flush_bytes=cache_flush_bytes,
            skip_reason=f"lut_table_bytes>{max_lut_table_bytes}",
        )

    row_start = time.perf_counter()
    predictions = predict_cache_widths(input_width, output_width)
    chunks, chunked, chunk_size = _make_chunks(
        input_width=input_width,
        batch_size=batch_size,
        max_in_memory_rows=max_in_memory_rows,
        rng=rng,
    )
    build_start = time.perf_counter()
    try:
        kernel = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=16 if output_width <= 16 else 32)
    except MemoryError:
        return _empty_row(
            spec=spec,
            task=task,
            measurement_mode=measurement_mode,
            block_width=block_width,
            batch_size=batch_size,
            input_width=input_width,
            output_width=output_width,
            env=env,
            seed=seed,
            warmups=warmups,
            repeats=repeats,
            affinity_status=affinity_status,
            frequency_lock_status=frequency_lock_status,
            cache_flush_bytes=cache_flush_bytes,
            skip_reason="MemoryError while building LUT",
        )
    kernel_build_s = time.perf_counter() - build_start
    exact_start = time.perf_counter()
    expected = pack_batch(NaiveGF2Kernel(matrix).apply_many(chunks[0]))
    actual = kernel.apply_many_packed(chunks[0])
    correctness_passed = bool(np.array_equal(actual, expected))
    exactness_elapsed_s = time.perf_counter() - exact_start
    samples: list[float] = []
    timing_elapsed_s = 0.0
    timed = False
    skip_reason = ""
    cache_flush = None
    if measurement_mode == "cache_flushed_dram_proxy":
        cache_flush = np.ones(max(0, int(cache_flush_bytes)), dtype=np.uint8)
    if correctness_passed:
        stream_fn = _make_stream_fn(kernel.apply_many_packed, chunks, cache_flush)
        timing_start = time.perf_counter()
        samples = _time_samples(stream_fn, warmups=warmups, repeats=repeats)
        timing_elapsed_s = time.perf_counter() - timing_start
        timed = True
    else:
        skip_reason = "exactness failed"
    summary = _summary(samples)
    median = summary["median_runtime_s"]
    processed_bits = int(batch_size) * int(input_width)
    row = {
        "profile": spec.profile,
        "task": task,
        "measurement_mode": measurement_mode,
        "block_width": int(block_width),
        "batch_size": int(batch_size),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "lut_table_bytes": lut_bytes,
        "cache_level_fit": cache_level_fit(lut_bytes),
        "theoretical_ops": theoretical_ops(input_width, output_width, block_width),
        "theoretical_continuous_ops": theoretical_continuous_ops(input_width, output_width, block_width),
        "predicted_l1_w": predictions["L1"],
        "predicted_l2_w": predictions["L2"],
        "predicted_l3_w": predictions["L3"],
        "backend": "PackedBlockLUTKernel.apply_many_packed",
        "processed_bits": processed_bits,
        "packed_word_bits": 16 if output_width <= 16 else 32,
        "chunked_online": chunked,
        "chunk_size": chunk_size,
        "build_init_s": float(spec.init_elapsed_s),
        "kernel_build_s": kernel_build_s,
        "exactness_elapsed_s": exactness_elapsed_s,
        "timing_elapsed_s": timing_elapsed_s,
        "elapsed_s": time.perf_counter() - row_start,
        **summary,
        "throughput_Mbit_s": processed_bits / median / 1_000_000.0 if median > 0 else 0.0,
        "throughput_Mcodeword_s": int(batch_size) / median / 1_000_000.0 if median > 0 else 0.0,
        "ns_per_bit": median * 1_000_000_000.0 / processed_bits if processed_bits > 0 and median > 0 else 0.0,
        "samples_s": ";".join(f"{sample:.12g}" for sample in samples),
        "warmups": int(warmups),
        "repeats": int(repeats),
        "correctness_passed": correctness_passed,
        "timed": timed,
        "skip_reason": skip_reason,
        "affinity_status": affinity_status,
        "frequency_lock_status": frequency_lock_status,
        "cache_flush_bytes": int(cache_flush_bytes if measurement_mode == "cache_flushed_dram_proxy" else 0),
        "measurement_order": "interleaved_by_width",
        **env,
        "seed": int(seed),
        "notes": "cache-flushed DRAM proxy" if measurement_mode == "cache_flushed_dram_proxy" else "natural placement",
    }
    return {field: row.get(field, "") for field in FIELDNAMES}


def run_round31_cache_width_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    profile_keys: tuple[str, ...] = DEFAULT_PROFILES,
    task: str = "syndrome",
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    block_widths: tuple[int, ...] = DEFAULT_BLOCK_WIDTHS,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    max_in_memory_rows: int = DEFAULT_MAX_IN_MEMORY_ROWS,
    max_lut_table_bytes: int = DEFAULT_MAX_LUT_TABLE_BYTES,
    seed: int = RNG_SEED,
    cpu_core: int | None = None,
    measurement_modes: tuple[str, ...] = ("natural",),
    cache_flush_bytes: int | None = None,
) -> list[dict[str, Any]]:
    affinity_status = _try_set_affinity(cpu_core)
    frequency_status = _frequency_lock_status()
    env = environment_fields()
    specs = matrix_specs or build_round31_matrix_specs(profile_keys)
    rng = np.random.default_rng(seed)
    flush_bytes = cache_flush_bytes
    if flush_bytes is None:
        cache = get_cache_profile()
        flush_bytes = max(int(cache.l3_bytes) * 2, 64 * 1024 * 1024)
    configs = []
    for width in block_widths:
        for spec in specs:
            matrix = _as_gf2_matrix(spec.matrix)
            task_matrix = matrix[: spec.k] if task == "parity" else matrix
            for batch_size in batch_sizes:
                for mode in measurement_modes:
                    configs.append((spec, task_matrix, int(width), int(batch_size), mode))
    rows = []
    for spec, task_matrix, width, batch_size, mode in configs:
        rows.append(
            _bench_one(
                spec=spec,
                task=task,
                matrix=task_matrix,
                measurement_mode=mode,
                block_width=width,
                batch_size=batch_size,
                warmups=warmups,
                repeats=repeats,
                max_in_memory_rows=max_in_memory_rows,
                max_lut_table_bytes=max_lut_table_bytes,
                rng=rng,
                env=env,
                seed=seed,
                affinity_status=affinity_status,
                frequency_lock_status=frequency_status,
                cache_flush_bytes=int(flush_bytes),
            )
        )
    return rows


def _parse_profile_keys(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_modes(value: str) -> tuple[str, ...]:
    modes = tuple(part.strip() for part in value.split(",") if part.strip())
    valid = {"natural", "cache_flushed_dram_proxy"}
    invalid = [mode for mode in modes if mode not in valid]
    if invalid:
        raise ValueError(f"invalid measurement modes: {invalid}")
    return modes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Round 31 cache-width sweep.")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES))
    parser.add_argument("--task", choices=("syndrome", "parity"), default="syndrome")
    parser.add_argument("--batch-sizes", default=",".join(str(value) for value in DEFAULT_BATCH_SIZES))
    parser.add_argument("--block-widths", default=",".join(str(value) for value in DEFAULT_BLOCK_WIDTHS))
    parser.add_argument("--measurement-modes", default="natural")
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--max-lut-table-bytes", type=int, default=DEFAULT_MAX_LUT_TABLE_BYTES)
    parser.add_argument("--cache-flush-bytes", type=int, default=0)
    parser.add_argument("--cpu-core", type=int, default=None)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--output", type=Path, default=RAW_DIR / "round31_block_width_cache_sweep.csv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_round31_cache_width_rows(
        profile_keys=_parse_profile_keys(args.profiles),
        task=args.task,
        batch_sizes=_parse_int_list(args.batch_sizes),
        block_widths=_parse_int_list(args.block_widths),
        measurement_modes=_parse_modes(args.measurement_modes),
        repeats=args.repeats,
        warmups=args.warmups,
        max_in_memory_rows=args.max_in_memory_rows,
        max_lut_table_bytes=args.max_lut_table_bytes,
        cache_flush_bytes=args.cache_flush_bytes or None,
        cpu_core=args.cpu_core,
        seed=args.seed,
    )
    write_csv(args.output, rows)
    print(f"wrote {args.output}")
    skipped = [row for row in rows if str(row["timed"]) != "True"]
    if skipped:
        print(f"WARNING: {len(skipped)} rows were not timed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
