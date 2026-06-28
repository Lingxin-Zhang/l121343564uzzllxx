"""Round 33 dense-batch Fig. 3 benchmark.

This runner is scoped to fixed block width ``w=14``. It measures bulk
``apply_many`` throughput, fixed-chunk streaming throughput, and a diagnostic
stage breakdown for ``PackedBlockLUTKernel``.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs
from benchmarks.bench_fixed_map_three_backend import _parse_int_list, _random_batch, pack_batch
from benchmarks.bench_round31_cache_width import (
    _parse_profile_keys,
    _try_set_affinity,
    build_round31_matrix_specs,
    lut_table_bytes,
)
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel

DEFAULT_BATCHES = (10, 30, 100, 300, 500, 700, 1_000, 1_500, 2_000, 3_000, 5_000, 7_000, 10_000, 30_000, 100_000, 300_000, 1_000_000, 3_000_000)
DEFAULT_OUTPUT = RAW_DIR / "round33_fig3_dense_batch_rows.csv"
DEFAULT_STAGE_OUTPUT = RAW_DIR / "round33_fig3_stage_breakdown_rows.csv"
BACKEND_DIRECT = "PackedBatchGF2Kernel.apply_many"
BACKEND_LUT = "PackedBlockLUTKernel.apply_many_packed"


class IncrementalCsvWriter:
    """Write benchmark rows as soon as each point finishes."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._writer: csv.DictWriter | None = None
        self._wrote = False

    def write(self, row: dict[str, Any]) -> None:
        if self._writer is None:
            self._file = self.path.open("w", newline="", encoding="utf-8")
            self._writer = csv.DictWriter(self._file, fieldnames=list(row.keys()))
            self._writer.writeheader()
        self._writer.writerow(row)
        self._wrote = True
        assert self._file is not None
        self._file.flush()

    def close(self) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None

    def ensure_exists(self) -> None:
        if not self._wrote:
            self.path.write_text("", encoding="utf-8")


def make_stream_chunks(total_rows: int, chunk_rows: int) -> tuple[int, ...]:
    total_rows = int(total_rows)
    chunk_rows = int(chunk_rows)
    if total_rows <= 0 or chunk_rows <= 0:
        raise ValueError("total_rows and chunk_rows must be positive")
    full, rem = divmod(total_rows, chunk_rows)
    chunks = [chunk_rows] * full
    if rem:
        chunks.append(rem)
    return tuple(chunks)


def staged_apply_many_packed(kernel: PackedBlockLUTKernel, x_batch: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    """Apply ``kernel`` with coarse stage timing.

    The read/prepare stage materializes each local block slice. This is a
    diagnostic decomposition, not a byte-for-byte replacement of the production
    kernel's implementation strategy.
    """

    x_batch = np.asarray(x_batch, dtype=np.uint8)
    acc = np.zeros(x_batch.shape[0], dtype=kernel.packed_dtype)
    times = {
        "stage_read_prepare_s": 0.0,
        "stage_index_s": 0.0,
        "stage_lookup_s": 0.0,
        "stage_xor_s": 0.0,
        "stage_write_s": 0.0,
    }
    for start, end, bit_weights, table in kernel.blocks:
        t0 = time.perf_counter()
        local_bits = np.ascontiguousarray(x_batch[:, start:end])
        times["stage_read_prepare_s"] += time.perf_counter() - t0

        t0 = time.perf_counter()
        masks = (local_bits @ bit_weights).astype(np.intp, copy=False)
        times["stage_index_s"] += time.perf_counter() - t0

        t0 = time.perf_counter()
        values = table[masks]
        times["stage_lookup_s"] += time.perf_counter() - t0

        t0 = time.perf_counter()
        acc ^= values
        times["stage_xor_s"] += time.perf_counter() - t0

    t0 = time.perf_counter()
    out = acc.copy()
    times["stage_write_s"] += time.perf_counter() - t0
    return out, times


def _summary(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "median_runtime_s": 0.0,
            "min_runtime_s": 0.0,
            "max_runtime_s": 0.0,
            "stdev_runtime_s": 0.0,
            "cv": 0.0,
        }
    median = statistics.median(samples)
    stdev = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "median_runtime_s": median,
        "min_runtime_s": min(samples),
        "max_runtime_s": max(samples),
        "stdev_runtime_s": stdev,
        "cv": stdev / median if median > 0 else 0.0,
    }


def _time_samples(fn, *, warmups: int, repeats: int) -> list[float]:
    for _ in range(int(warmups)):
        fn()
    samples: list[float] = []
    for _ in range(int(repeats)):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _task_matrix(spec, task: str) -> np.ndarray:
    matrix = np.asarray(spec.matrix, dtype=np.uint8) & 1
    return matrix[: spec.k] if task == "parity" else matrix


def _backend_fn(
    *,
    backend: str,
    matrix: np.ndarray,
    block_width: int,
) -> tuple[Any, str]:
    if backend == BACKEND_DIRECT:
        kernel = PackedBatchGF2Kernel(matrix)
        return kernel.apply_many, "bits"
    if backend == BACKEND_LUT:
        kernel = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=16 if matrix.shape[1] <= 16 else 32)
        return kernel.apply_many_packed, "packed"
    raise ValueError(f"unknown backend {backend}")


def _stream_fn(fn, x_full: np.ndarray, x_rem: np.ndarray | None, chunks: tuple[int, ...]):
    def run():
        last = None
        for rows in chunks:
            if rows == x_full.shape[0]:
                last = fn(x_full)
            else:
                assert x_rem is not None
                last = fn(x_rem)
        return last

    return run


def _row_for_backend(
    *,
    spec,
    task: str,
    matrix: np.ndarray,
    backend: str,
    mode: str,
    batch_size: int,
    block_width: int,
    round_index: int,
    repeats: int,
    warmups: int,
    stream_chunk_size: int,
    max_bulk_rows: int,
    seed: int,
    rng: np.random.Generator,
    affinity_status: str,
) -> dict[str, Any]:
    input_width, output_width = matrix.shape
    processed_bits = int(batch_size) * int(input_width)
    row_start = time.perf_counter()
    timed = False
    correctness_passed = False
    skip_reason = ""
    samples: list[float] = []
    chunk_plan = ""
    active_rows = int(batch_size)

    try:
        fn, output_kind = _backend_fn(backend=backend, matrix=matrix, block_width=block_width)
        exact_rows = min(int(batch_size), 256)
        exact_batch = _random_batch(input_width, exact_rows, rng)
        expected_bits = NaiveGF2Kernel(matrix).apply_many(exact_batch)
        expected = pack_batch(expected_bits) if output_kind == "packed" else expected_bits
        correctness_passed = bool(np.array_equal(fn(exact_batch), expected))

        if not correctness_passed:
            skip_reason = "exactness failed"
        elif mode == "bulk" and int(batch_size) > int(max_bulk_rows):
            skip_reason = f"batch_size>{max_bulk_rows}"
        else:
            if mode == "bulk":
                x_batch = _random_batch(input_width, int(batch_size), rng)
                run = lambda: fn(x_batch)
            elif mode == "stream_chunked":
                chunks = make_stream_chunks(int(batch_size), int(stream_chunk_size))
                chunk_plan = ";".join(str(v) for v in chunks)
                active_rows = min(int(batch_size), int(stream_chunk_size))
                x_full = _random_batch(input_width, min(int(stream_chunk_size), int(batch_size)), rng)
                remainder = chunks[-1] if chunks[-1] != x_full.shape[0] else 0
                x_rem = _random_batch(input_width, remainder, rng) if remainder else None
                run = _stream_fn(fn, x_full, x_rem, chunks)
            else:
                raise ValueError(f"unknown mode {mode}")
            samples = _time_samples(run, warmups=warmups, repeats=repeats)
            timed = True
    except MemoryError:
        skip_reason = "MemoryError"

    summary = _summary(samples)
    median = summary["median_runtime_s"]
    throughput = processed_bits / median / 1_000_000.0 if median > 0 else 0.0
    return {
        "profile": spec.profile,
        "task": task,
        "mode": mode,
        "backend": backend,
        "round_index": int(round_index),
        "batch_size": int(batch_size),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "processed_bits": int(processed_bits),
        "block_width": int(block_width) if backend == BACKEND_LUT else "",
        "lut_table_bytes": lut_table_bytes(input_width, output_width, block_width) if backend == BACKEND_LUT else "",
        "stream_chunk_size": int(stream_chunk_size) if mode == "stream_chunked" else "",
        "stream_chunk_plan": chunk_plan,
        "active_input_bytes": active_rows * input_width / 8.0,
        "l1_fit_active_input": (active_rows * input_width / 8.0) <= 32_768,
        "warmups": int(warmups),
        "repeats": int(repeats),
        "timed": timed,
        "correctness_passed": correctness_passed,
        "skip_reason": skip_reason,
        **summary,
        "throughput_Mbit_s": throughput,
        "throughput_Mcodeword_s": int(batch_size) / median / 1_000_000.0 if median > 0 else 0.0,
        "ns_per_bit": median * 1_000_000_000.0 / processed_bits if processed_bits > 0 and median > 0 else 0.0,
        "samples_s": ";".join(f"{sample:.12g}" for sample in samples),
        "elapsed_s": time.perf_counter() - row_start,
        "affinity_status": affinity_status,
        "seed": int(seed),
    }


def _stage_row(
    *,
    spec,
    task: str,
    matrix: np.ndarray,
    batch_size: int,
    block_width: int,
    round_index: int,
    repeats: int,
    warmups: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    input_width, output_width = matrix.shape
    x_batch = _random_batch(input_width, int(batch_size), rng)
    kernel = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=16 if output_width <= 16 else 32)
    for _ in range(int(warmups)):
        staged_apply_many_packed(kernel, x_batch)
    stage_samples: dict[str, list[float]] = {}
    total_samples: list[float] = []
    correctness_passed = False
    for _ in range(int(repeats)):
        out, times = staged_apply_many_packed(kernel, x_batch)
        correctness_passed = bool(np.array_equal(out, kernel.apply_many_packed(x_batch)))
        total = sum(times.values())
        total_samples.append(total)
        for key, value in times.items():
            stage_samples.setdefault(key, []).append(value)
    row: dict[str, Any] = {
        "profile": spec.profile,
        "task": task,
        "batch_size": int(batch_size),
        "round_index": int(round_index),
        "block_width": int(block_width),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "active_input_bytes": int(batch_size) * input_width / 8.0,
        "l1_fit_active_input": (int(batch_size) * input_width / 8.0) <= 32_768,
        "correctness_passed": correctness_passed,
        "stage_total_s": statistics.median(total_samples) if total_samples else 0.0,
        "stage_repeats": int(repeats),
    }
    total = row["stage_total_s"]
    for key, values in stage_samples.items():
        median = statistics.median(values)
        row[key] = median
        row[key.replace("_s", "_pct")] = 100.0 * median / total if total > 0 else 0.0
    return row


def run_round33_rows(
    *,
    profiles: tuple[str, ...],
    tasks: tuple[str, ...],
    batch_sizes: tuple[int, ...],
    modes: tuple[str, ...],
    round_start: int,
    rounds: int,
    repeats: int,
    warmups: int,
    stage_repeats: int,
    stage_warmups: int,
    block_width: int,
    stream_chunk_size: int,
    max_bulk_rows: int,
    seed: int,
    cpu_core: int | None,
    include_stage: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    for kind, row in iter_round33_rows(
        profiles=profiles,
        tasks=tasks,
        batch_sizes=batch_sizes,
        modes=modes,
        round_start=round_start,
        rounds=rounds,
        repeats=repeats,
        warmups=warmups,
        stage_repeats=stage_repeats,
        stage_warmups=stage_warmups,
        block_width=block_width,
        stream_chunk_size=stream_chunk_size,
        max_bulk_rows=max_bulk_rows,
        seed=seed,
        cpu_core=cpu_core,
        include_stage=include_stage,
    ):
        if kind == "throughput":
            rows.append(row)
        else:
            stage_rows.append(row)
    return rows, stage_rows


def iter_round33_rows(
    *,
    profiles: tuple[str, ...],
    tasks: tuple[str, ...],
    batch_sizes: tuple[int, ...],
    modes: tuple[str, ...],
    round_start: int,
    rounds: int,
    repeats: int,
    warmups: int,
    stage_repeats: int,
    stage_warmups: int,
    block_width: int,
    stream_chunk_size: int,
    max_bulk_rows: int,
    seed: int,
    cpu_core: int | None,
    include_stage: bool,
):
    affinity_status = _try_set_affinity(cpu_core)
    specs = build_round31_matrix_specs(profiles)
    for round_offset in range(int(rounds)):
        round_index = int(round_start) + round_offset
        rng = np.random.default_rng(int(seed) + round_index)
        for spec in specs:
            for task in tasks:
                matrix = _task_matrix(spec, task)
                for batch_size in batch_sizes:
                    for mode in modes:
                        for backend in (BACKEND_DIRECT, BACKEND_LUT):
                            yield (
                                "throughput",
                                _row_for_backend(
                                    spec=spec,
                                    task=task,
                                    matrix=matrix,
                                    backend=backend,
                                    mode=mode,
                                    batch_size=int(batch_size),
                                    block_width=int(block_width),
                                    round_index=round_index,
                                    repeats=int(repeats),
                                    warmups=int(warmups),
                                    stream_chunk_size=int(stream_chunk_size),
                                    max_bulk_rows=int(max_bulk_rows),
                                    seed=int(seed),
                                    rng=rng,
                                    affinity_status=affinity_status,
                                ),
                            )
                    if include_stage:
                        yield (
                            "stage",
                            _stage_row(
                                spec=spec,
                                task=task,
                                matrix=matrix,
                                batch_size=int(batch_size),
                                block_width=int(block_width),
                                round_index=round_index,
                                repeats=int(stage_repeats),
                                warmups=int(stage_warmups),
                                rng=rng,
                            ),
                        )


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _parse_tasks(value: str) -> tuple[str, ...]:
    tasks = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = [task for task in tasks if task not in {"syndrome", "parity"}]
    if invalid:
        raise ValueError(f"invalid tasks: {invalid}")
    return tasks


def _parse_modes(value: str) -> tuple[str, ...]:
    modes = tuple(part.strip() for part in value.split(",") if part.strip())
    invalid = [mode for mode in modes if mode not in {"bulk", "stream_chunked"}]
    if invalid:
        raise ValueError(f"invalid modes: {invalid}")
    return modes


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Round33 dense-batch Fig3 benchmark.")
    parser.add_argument("--profiles", default="255_239")
    parser.add_argument("--tasks", default="syndrome,parity")
    parser.add_argument("--batch-sizes", default=",".join(str(v) for v in DEFAULT_BATCHES))
    parser.add_argument("--modes", default="bulk,stream_chunked")
    parser.add_argument("--round-start", type=int, default=0)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=15)
    parser.add_argument("--warmups", type=int, default=30)
    parser.add_argument("--stage-repeats", type=int, default=5)
    parser.add_argument("--stage-warmups", type=int, default=5)
    parser.add_argument("--block-width", type=int, default=14)
    parser.add_argument("--stream-chunk-size", type=int, default=1000)
    parser.add_argument("--max-bulk-rows", type=int, default=3_000_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu-core", type=int, default=None)
    parser.add_argument("--no-stage", action="store_true")
    parser.add_argument("--buffered-write", action="store_true", help="Collect rows in memory and write CSVs at the end.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--stage-output", type=Path, default=DEFAULT_STAGE_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    parsed = {
        "profiles": _parse_profile_keys(args.profiles),
        "tasks": _parse_tasks(args.tasks),
        "batch_sizes": _parse_int_list(args.batch_sizes),
        "modes": _parse_modes(args.modes),
        "round_start": args.round_start,
        "rounds": args.rounds,
        "repeats": args.repeats,
        "warmups": args.warmups,
        "stage_repeats": args.stage_repeats,
        "stage_warmups": args.stage_warmups,
        "block_width": args.block_width,
        "stream_chunk_size": args.stream_chunk_size,
        "max_bulk_rows": args.max_bulk_rows,
        "seed": args.seed,
        "cpu_core": args.cpu_core,
        "include_stage": not args.no_stage,
    }
    if args.buffered_write:
        rows, stage_rows = run_round33_rows(**parsed)
        write_rows(args.output, rows)
        write_rows(args.stage_output, stage_rows)
    else:
        throughput_writer = IncrementalCsvWriter(args.output)
        stage_writer = IncrementalCsvWriter(args.stage_output)
        try:
            for kind, row in iter_round33_rows(**parsed):
                if kind == "throughput":
                    throughput_writer.write(row)
                else:
                    stage_writer.write(row)
        finally:
            throughput_writer.close()
            stage_writer.close()
            throughput_writer.ensure_exists()
            stage_writer.ensure_exists()
    print(f"wrote {args.output}")
    print(f"wrote {args.stage_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
