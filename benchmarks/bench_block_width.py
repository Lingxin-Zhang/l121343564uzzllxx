"""Benchmark block width against per-word latency and LUT size."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from linear_kernel import (
    BlockLUTKernel,
    NaiveGF2Kernel,
    PackedBlockLUTKernel,
    SparseXorKernel,
)

from benchmarks._common import (
    RAW_DIR,
    block_lut_table_size_bytes,
    ensure_result_dirs,
    make_batch,
    make_matrix,
    summarize_per_word,
    time_repeats,
    write_csv,
)

BLOCK_WIDTHS = (4, 6, 8, 10, 12, 14, 16, 18, 20)
DEFAULT_DENSITY = 0.05
DEFAULT_WORDS = 512
DEFAULT_REPEATS = 5
RNG_SEED = 20260629


def _run_apply_loop(kernel: Any, x_batch) -> None:
    for x in x_batch:
        kernel.apply(x)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", type=int, default=DEFAULT_WORDS)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = make_matrix()
    x_batch = make_batch(np.random.default_rng(RNG_SEED), args.words, args.density)
    rows: list[dict[str, Any]] = []

    for block_width in BLOCK_WIDTHS:
        backends = [
            ("Naive", NaiveGF2Kernel(matrix), 0),
            ("SparseXor", SparseXorKernel(matrix), 0),
        ]
        block_kernel = BlockLUTKernel(matrix, block_width=block_width)
        backends.append(
            ("BlockLUT", block_kernel, block_lut_table_size_bytes(block_kernel))
        )
        packed_block_kernel = PackedBlockLUTKernel(matrix, block_width=block_width)
        backends.append(
            (
                "PackedBlockLUT",
                packed_block_kernel,
                block_lut_table_size_bytes(packed_block_kernel),
            )
        )

        expected = backends[0][1].apply_many(x_batch)
        for backend_name, kernel, table_size_bytes in backends:
            actual = kernel.apply_many(x_batch)
            if not (actual == expected).all():
                raise AssertionError(f"{backend_name} disagrees with Naive")

            samples = time_repeats(
                lambda kernel=kernel: _run_apply_loop(kernel, x_batch),
                repeats=args.repeats,
            )
            summary = summarize_per_word(samples, args.words)
            rows.append(
                {
                    "backend": backend_name,
                    "block_width": block_width,
                    "density": args.density,
                    "latency_per_word_us": summary["latency_per_word_us"],
                    "throughput_words_per_sec": summary["throughput_words_per_sec"],
                    "table_size_bytes": table_size_bytes,
                    "repeats": args.repeats,
                    "mean": summary["mean"],
                    "std": summary["std"],
                }
            )

    output = RAW_DIR / "block_width.csv"
    write_csv(output, rows)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
