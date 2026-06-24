"""Benchmark backend latency across input densities."""

from __future__ import annotations

import argparse
from typing import Any

import numpy as np

from linear_kernel import (
    BlockLUTKernel,
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    SparseXorKernel,
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

DENSITIES = (0.005, 0.01, 0.02, 0.05, 0.1, 0.5)
DEFAULT_BATCH_SIZE = 1024
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 5
RNG_SEED = 20260630


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = make_matrix()
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, Any]] = []

    backends = [
        ("Naive", NaiveGF2Kernel(matrix), 0),
        ("SparseXor", SparseXorKernel(matrix), 0),
    ]
    block_kernel = BlockLUTKernel(matrix, block_width=args.block_width)
    backends.append(("BlockLUT", block_kernel, block_lut_table_size_bytes(block_kernel)))
    backends.append(("PackedBatch", PackedBatchGF2Kernel(matrix), 0))

    for density in DENSITIES:
        x_batch = make_batch(rng, args.batch_size, density)
        expected = backends[0][1].apply_many(x_batch)

        for backend_name, kernel, table_size_bytes in backends:
            actual = kernel.apply_many(x_batch)
            if not (actual == expected).all():
                raise AssertionError(f"{backend_name} disagrees with Naive")

            samples = time_repeats(
                lambda kernel=kernel: kernel.apply_many(x_batch),
                repeats=args.repeats,
            )
            summary = summarize_per_word(samples, args.batch_size)
            rows.append(
                {
                    "backend": backend_name,
                    "density": density,
                    "batch_size": args.batch_size,
                    "block_width": args.block_width,
                    "latency_per_word_us": summary["latency_per_word_us"],
                    "throughput_words_per_sec": summary["throughput_words_per_sec"],
                    "table_size_bytes": table_size_bytes,
                    "repeats": args.repeats,
                    "mean": summary["mean"],
                    "std": summary["std"],
                }
            )

    output = RAW_DIR / "density.csv"
    write_csv(output, mark_fastest(rows, "density"))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
