"""Benchmark repeated component syndrome computation loops."""

from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Callable
from typing import Any

import numpy as np

from benchmarks._common import (
    RAW_DIR,
    block_lut_table_size_bytes,
    ensure_result_dirs,
    make_batch,
    write_csv,
)
from codes.matrix_sources import get_matrix_source
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16

DEFAULT_MATRIX_SOURCE = "galois_systematic_candidate"
DEFAULT_NUM_WORDS = (4096, 16384, 65536)
DEFAULT_ITERATIONS = (1, 5, 10)
DEFAULT_CHUNK_WORDS = 4096
DEFAULT_DENSITY = 0.05
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 3
RNG_SEED = 20260706


Backend = tuple[str, Callable[[np.ndarray], np.ndarray], int, str]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _iter_chunks(x_words: np.ndarray, chunk_words: int):
    for start in range(0, x_words.shape[0], chunk_words):
        yield x_words[start : start + chunk_words]


def _make_backends(matrix: np.ndarray, block_width: int) -> tuple[NaiveGF2Kernel, list[Backend]]:
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_block = PackedBlockLUTKernel(matrix, block_width=block_width)
    packed_block_table_size = block_lut_table_size_bytes(packed_block)
    return naive, [
        ("Naive.apply_many", naive.apply_many, 0, "unpacked"),
        ("PackedBatch.apply_many", packed_batch.apply_many, 0, "unpacked"),
        (
            "PackedBlockLUT.apply_many",
            packed_block.apply_many,
            packed_block_table_size,
            "unpacked",
        ),
        (
            "PackedBlockLUT.apply_many_packed",
            packed_block.apply_many_packed,
            packed_block_table_size,
            "packed",
        ),
    ]


def _verify_component_outputs(
    x_words: np.ndarray,
    chunk_words: int,
    naive: NaiveGF2Kernel,
    backends: list[Backend],
) -> bool:
    for chunk in _iter_chunks(x_words, chunk_words):
        expected = naive.apply_many(chunk)
        expected_packed = pack_batch_bits_to_uint16(expected)
        for backend_name, fn, _, output_kind in backends:
            actual = fn(chunk)
            expected_output = expected_packed if output_kind == "packed" else expected
            if not np.array_equal(actual, expected_output):
                raise AssertionError(f"{backend_name} disagrees with Naive")
    return True


def check_component_loop_correctness(
    matrix_source: str,
    num_words: int,
    chunk_words: int,
    density: float,
    block_width: int,
) -> bool:
    matrix = get_matrix_source(matrix_source)
    rng = np.random.default_rng(RNG_SEED)
    x_words = make_batch(rng, num_words, density, n=matrix.shape[0])
    naive, backends = _make_backends(matrix, block_width)
    return _verify_component_outputs(x_words, chunk_words, naive, backends)


def _run_loop(
    x_words: np.ndarray,
    chunk_words: int,
    iterations: int,
    fn: Callable[[np.ndarray], np.ndarray],
) -> None:
    for _ in range(iterations):
        for chunk in _iter_chunks(x_words, chunk_words):
            fn(chunk)


def _time_loop(
    x_words: np.ndarray,
    chunk_words: int,
    iterations: int,
    fn: Callable[[np.ndarray], np.ndarray],
    repeats: int,
) -> list[float]:
    _run_loop(x_words, chunk_words, iterations, fn)
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        _run_loop(x_words, chunk_words, iterations, fn)
        samples.append(time.perf_counter() - start)
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-source", default=DEFAULT_MATRIX_SOURCE)
    parser.add_argument("--num-words", default=",".join(str(x) for x in DEFAULT_NUM_WORDS))
    parser.add_argument("--iterations", default=",".join(str(x) for x in DEFAULT_ITERATIONS))
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = get_matrix_source(args.matrix_source)
    component_n, output_r = matrix.shape
    rng = np.random.default_rng(RNG_SEED)
    naive, backends = _make_backends(matrix, args.block_width)
    rows: list[dict[str, Any]] = []

    for num_words in _parse_int_list(args.num_words):
        x_words = make_batch(rng, num_words, args.density, n=component_n)
        correctness_passed = _verify_component_outputs(
            x_words=x_words,
            chunk_words=args.chunk_words,
            naive=naive,
            backends=backends,
        )
        for iterations in _parse_int_list(args.iterations):
            processed_words = num_words * iterations
            processed_bits = processed_words * component_n
            for backend_name, fn, table_size_bytes, _ in backends:
                samples = _time_loop(
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
                        "matrix_source": args.matrix_source,
                        "backend": backend_name,
                        "component_n": component_n,
                        "output_r": output_r,
                        "num_words": num_words,
                        "chunk_words": args.chunk_words,
                        "iterations": iterations,
                        "density": args.density,
                        "block_width": args.block_width,
                        "total_runtime_s": mean,
                        "throughput_Mword_s": processed_words / mean / 1_000_000.0,
                        "throughput_Mbit_s": processed_bits / mean / 1_000_000.0,
                        "latency_per_word_us": mean / processed_words * 1_000_000.0,
                        "table_size_bytes": table_size_bytes,
                        "repeats": args.repeats,
                        "mean": mean,
                        "std": std,
                        "correctness_passed": correctness_passed,
                    }
                )

    output = RAW_DIR / "component_loop.csv"
    write_csv(output, rows)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
