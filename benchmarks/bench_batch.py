"""Benchmark batch-size crossover for batch-capable backends."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from linear_kernel import (
    BlockLUTKernel,
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    PackedBlockLUTKernel,
)

from benchmarks._common import (
    RAW_DIR,
    block_lut_table_size_bytes,
    ensure_result_dirs,
    make_batch,
    make_matrix,
    mark_fastest,
    summarize_per_word,
    time_repeats,
    write_csv,
)

BATCH_SIZES = (1, 4, 16, 64, 256, 1024, 4096)
DEFAULT_DENSITY = 0.05
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 5
RNG_SEED = 20260701


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = make_matrix()
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, Any]] = []

    naive = NaiveGF2Kernel(matrix)
    block_kernel = BlockLUTKernel(matrix, block_width=args.block_width)
    packed_block_kernel = PackedBlockLUTKernel(matrix, block_width=args.block_width)
    packed = PackedBatchGF2Kernel(matrix)
    backends = [
        ("Naive.apply_many", naive, 0),
        ("BlockLUT.apply_many", block_kernel, block_lut_table_size_bytes(block_kernel)),
        (
            "PackedBlockLUT.apply_many",
            packed_block_kernel,
            block_lut_table_size_bytes(packed_block_kernel),
        ),
        ("PackedBatch.apply_many", packed, 0),
    ]

    for batch_size in BATCH_SIZES:
        x_batch = make_batch(rng, batch_size, args.density)
        expected = naive.apply_many(x_batch)

        for backend_name, kernel, table_size_bytes in backends:
            actual = kernel.apply_many(x_batch)
            if not (actual == expected).all():
                raise AssertionError(f"{backend_name} disagrees with Naive")

            samples = time_repeats(
                lambda kernel=kernel: kernel.apply_many(x_batch),
                repeats=args.repeats,
            )
            summary = summarize_per_word(samples, batch_size)
            rows.append(
                {
                    "backend": backend_name,
                    "batch_size": batch_size,
                    "density": args.density,
                    "block_width": args.block_width,
                    "latency_per_word_us": summary["latency_per_word_us"],
                    "throughput_words_per_sec": summary["throughput_words_per_sec"],
                    "table_size_bytes": table_size_bytes,
                    "repeats": args.repeats,
                    "mean": summary["mean"],
                    "std": summary["std"],
                }
            )

    output = RAW_DIR / "batch.csv"
    write_csv(output, mark_fastest(rows, "batch_size"))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
