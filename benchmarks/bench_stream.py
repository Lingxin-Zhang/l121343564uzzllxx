"""Benchmark chunked GF(2) processing for larger bit streams."""

from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel

from benchmarks._common import (
    N,
    R,
    RAW_DIR,
    block_lut_table_size_bytes,
    ensure_result_dirs,
    make_batch,
    make_matrix,
    write_csv,
)
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16

TOTAL_BITS = (1_000_000, 10_000_000)
ITERATIONS = (1, 5, 10)
DEFAULT_CHUNK_WORDS = 4096
DEFAULT_DENSITY = 0.05
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 3
RNG_SEED = 20260703


def _iter_chunks(x_words: np.ndarray, chunk_words: int):
    for start in range(0, x_words.shape[0], chunk_words):
        yield x_words[start : start + chunk_words]


def _run_stream(
    x_words: np.ndarray,
    chunk_words: int,
    iterations: int,
    fn: Callable[[np.ndarray], np.ndarray],
) -> None:
    for _ in range(iterations):
        for chunk in _iter_chunks(x_words, chunk_words):
            fn(chunk)


def _time_stream(
    x_words: np.ndarray,
    chunk_words: int,
    iterations: int,
    fn: Callable[[np.ndarray], np.ndarray],
    repeats: int,
) -> list[float]:
    _run_stream(x_words, chunk_words, iterations, fn)
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        _run_stream(x_words, chunk_words, iterations, fn)
        samples.append(time.perf_counter() - start)
    return samples


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-bits", default=",".join(str(x) for x in TOTAL_BITS))
    parser.add_argument("--iterations", default=",".join(str(x) for x in ITERATIONS))
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = make_matrix()
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, Any]] = []

    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_block = PackedBlockLUTKernel(matrix, block_width=args.block_width)
    backends = [
        ("Naive.apply_many", naive.apply_many, 0),
        ("PackedBatch.apply_many", packed_batch.apply_many, 0),
        (
            "PackedBlockLUT.apply_many_packed",
            packed_block.apply_many_packed,
            block_lut_table_size_bytes(packed_block),
        ),
    ]

    for total_bits in _parse_int_list(args.total_bits):
        num_words = total_bits // N
        if num_words < 1:
            raise ValueError("total_bits must contain at least one component word")
        x_words = make_batch(rng, num_words, args.density)
        first_chunk = x_words[: args.chunk_words]
        expected_first = naive.apply_many(first_chunk)
        expected_first_packed = pack_batch_bits_to_uint16(expected_first)

        for iterations in _parse_int_list(args.iterations):
            processed_bits = num_words * N * iterations
            processed_words = num_words * iterations
            for backend_name, fn, table_size_bytes in backends:
                actual_first = fn(first_chunk)
                expected_output = (
                    expected_first_packed
                    if backend_name.endswith("apply_many_packed")
                    else expected_first
                )
                if not (actual_first == expected_output).all():
                    raise AssertionError(f"{backend_name} disagrees with Naive")

                samples = _time_stream(
                    x_words=x_words,
                    chunk_words=args.chunk_words,
                    iterations=iterations,
                    fn=fn,
                    repeats=args.repeats,
                )
                mean = statistics.fmean(samples)
                std = statistics.stdev(samples) if len(samples) > 1 else 0.0
                rows.append(
                    {
                        "backend": backend_name,
                        "total_bits": total_bits,
                        "component_n": N,
                        "output_r": R,
                        "num_words": num_words,
                        "chunk_words": args.chunk_words,
                        "iterations": iterations,
                        "density": args.density,
                        "block_width": args.block_width,
                        "total_runtime_s": mean,
                        "throughput_Mbit_s": processed_bits / mean / 1_000_000.0,
                        "latency_per_word_us": mean / processed_words * 1_000_000.0,
                        "table_size_bytes": table_size_bytes,
                        "repeats": args.repeats,
                        "mean": mean,
                        "std": std,
                    }
                )

    output = RAW_DIR / "stream.csv"
    write_csv(output, rows)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
