"""Decode benchmark that swaps only the syndrome linear-map backend."""

from __future__ import annotations

import argparse
import csv
import itertools
import statistics
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, write_csv
from benchmarks.bench_fixed_map_three_backend import (
    DEFAULT_MAX_IN_MEMORY_ROWS,
    DEFAULT_REPEATS,
    DEFAULT_WARMUPS,
    MatrixSpec,
    _as_gf2_matrix,
    _parse_int_list,
    _summary,
    _time_samples,
    default_matrix_specs,
    environment_fields,
)
from decoders.bdd_lut import BDDLUTDecoder
from linear_kernel import NaiveGF2Kernel, PackedBlockLUTKernel

DEFAULT_BATCH_SIZES = (100, 1_000, 10_000, 100_000)
DEFAULT_BLOCK_WIDTH = 12
RNG_SEED = 20260731

FIELDNAMES = [
    "profile",
    "batch_size",
    "backend",
    "syndrome_backend",
    "error_locator",
    "n",
    "r",
    "t",
    "block_width",
    "packed_word_bits",
    "build_init_s",
    "exactness_elapsed_s",
    "timing_elapsed_s",
    "elapsed_s",
    "median_runtime_s",
    "min_runtime_s",
    "max_runtime_s",
    "cv",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "samples_s",
    "warmups",
    "repeats",
    "correctness_passed",
    "decision_mismatch_count",
    "status_mismatch_count",
    "corrected_word_mismatch_count",
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


def _correctable_error_words(n: int, batch_size: int, t: int) -> np.ndarray:
    patterns = [()]
    if t >= 1:
        patterns.extend((i,) for i in range(n))
    if t >= 2:
        patterns.extend(itertools.combinations(range(n), 2))
    words = np.zeros((int(batch_size), int(n)), dtype=np.uint8)
    for row in range(int(batch_size)):
        positions = patterns[row % len(patterns)]
        if positions:
            words[row, list(positions)] = 1
    return words


def _count_row_mismatches(left: np.ndarray, right: np.ndarray) -> int:
    if left.shape != right.shape:
        return max(left.shape[0], right.shape[0])
    if left.ndim == 1:
        return int(np.count_nonzero(left != right))
    return int(np.count_nonzero(np.any(left != right, axis=1)))


def _time_decode(fn: Callable[[], dict[str, np.ndarray]], warmups: int, repeats: int) -> list[float]:
    return _time_samples(fn, warmups=warmups, repeats=repeats)


def _row(
    *,
    spec: MatrixSpec,
    decoder: BDDLUTDecoder,
    words: np.ndarray,
    backend_name: str,
    syndrome_backend: object,
    reference: dict[str, np.ndarray],
    block_width: int | str,
    warmups: int,
    repeats: int,
    env: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    config_start = time.perf_counter()
    exact_start = time.perf_counter()
    actual = decoder.decode_words(words, syndrome_backend=syndrome_backend)
    decision_mismatches = _count_row_mismatches(reference["correction_masks"], actual["correction_masks"])
    status_mismatches = int(np.count_nonzero(reference["statuses"] != actual["statuses"]))
    corrected_mismatches = _count_row_mismatches(reference["corrected_words"], actual["corrected_words"])
    correctness_passed = decision_mismatches == 0 and status_mismatches == 0 and corrected_mismatches == 0
    exact_elapsed = time.perf_counter() - exact_start
    samples: list[float] = []
    timing_elapsed = 0.0
    timed = False
    if correctness_passed:
        fn = lambda: decoder.decode_words(words, syndrome_backend=syndrome_backend)
        timing_start = time.perf_counter()
        samples = _time_decode(fn, warmups, repeats)
        timing_elapsed = time.perf_counter() - timing_start
        timed = True
    summary = _summary(samples)
    median = summary["median_runtime_s"]
    batch_size, n = words.shape
    return {
        "profile": spec.profile,
        "batch_size": int(batch_size),
        "backend": backend_name,
        "syndrome_backend": backend_name,
        "error_locator": "BDDLUTDecoder syndrome-to-position LUT; unchanged",
        "n": int(decoder.n),
        "r": int(decoder.r),
        "t": int(decoder.t),
        "block_width": block_width,
        "packed_word_bits": 16 if decoder.r <= 16 else 32,
        "build_init_s": float(spec.init_elapsed_s),
        "exactness_elapsed_s": exact_elapsed,
        "timing_elapsed_s": timing_elapsed,
        "elapsed_s": time.perf_counter() - config_start,
        **summary,
        "throughput_Mbit_s": (batch_size * n) / median / 1_000_000.0 if median > 0 else 0.0,
        "throughput_Mcodeword_s": batch_size / median / 1_000_000.0 if median > 0 else 0.0,
        "samples_s": ";".join(f"{sample:.12g}" for sample in samples),
        "warmups": int(warmups),
        "repeats": int(repeats),
        "correctness_passed": correctness_passed,
        "decision_mismatch_count": int(decision_mismatches),
        "status_mismatch_count": int(status_mismatches),
        "corrected_word_mismatch_count": int(corrected_mismatches),
        "timed": timed,
        **env,
        "seed": int(seed),
        "notes": "decode wall-clock includes unchanged syndrome lookup and correction application",
    }


def run_decode_syndrome_accel_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    block_width: int = DEFAULT_BLOCK_WIDTH,
    t: int = 2,
    max_in_memory_rows: int = DEFAULT_MAX_IN_MEMORY_ROWS,
    seed: int = RNG_SEED,
) -> list[dict[str, Any]]:
    env = environment_fields()
    rows: list[dict[str, Any]] = []
    for raw_spec in matrix_specs or default_matrix_specs():
        matrix = _as_gf2_matrix(raw_spec.matrix)
        spec = MatrixSpec(raw_spec.profile, matrix, int(raw_spec.k), float(raw_spec.init_elapsed_s), raw_spec.bch)
        decoder = BDDLUTDecoder(matrix, t=t)
        for batch_size in batch_sizes:
            bounded_batch = min(int(batch_size), int(max_in_memory_rows))
            words = _correctable_error_words(matrix.shape[0], bounded_batch, t)
            naive_backend = NaiveGF2Kernel(matrix)
            reference = decoder.decode_words(words, syndrome_backend=naive_backend)
            lut_backend = PackedBlockLUTKernel(
                matrix,
                block_width=block_width,
                packed_word_bits=16 if matrix.shape[1] <= 16 else 32,
            )
            rows.append(
                _row(
                    spec=spec,
                    decoder=decoder,
                    words=words,
                    backend_name="NaiveGF2Kernel.apply_many",
                    syndrome_backend=naive_backend,
                    reference=reference,
                    block_width="reference",
                    warmups=warmups,
                    repeats=repeats,
                    env=env,
                    seed=seed,
                )
            )
            rows.append(
                _row(
                    spec=spec,
                    decoder=decoder,
                    words=words,
                    backend_name="PackedBlockLUTKernel.apply_many_packed",
                    syndrome_backend=lut_backend,
                    reference=reference,
                    block_width=block_width,
                    warmups=warmups,
                    repeats=repeats,
                    env=env,
                    seed=seed,
                )
            )
    return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]


def _write_or_append_csv(output: Path, rows: list[dict[str, Any]], append: bool) -> None:
    if append and output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            rows = [*list(csv.DictReader(f)), *rows]
    write_csv(output, rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run decode benchmark with syndrome backend swap only.")
    parser.add_argument("--batch-sizes", default=",".join(str(value) for value in DEFAULT_BATCH_SIZES))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--t", type=int, default=2)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--output", type=Path, default=RAW_DIR / "decode_syndrome_accel.csv")
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_decode_syndrome_accel_rows(
        batch_sizes=_parse_int_list(args.batch_sizes),
        repeats=args.repeats,
        warmups=args.warmups,
        block_width=args.block_width,
        t=args.t,
        max_in_memory_rows=args.max_in_memory_rows,
        seed=args.seed,
    )
    _write_or_append_csv(args.output, rows, args.append)
    print(f"wrote {args.output}")
    failed = [row for row in rows if row["correctness_passed"] is not True]
    if failed:
        print(f"WARNING: {len(failed)} rows failed decode decision exactness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
