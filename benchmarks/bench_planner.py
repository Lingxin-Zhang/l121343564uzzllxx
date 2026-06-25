"""Benchmark the simple rule-based HybridPlanner."""

from __future__ import annotations

import argparse
import statistics
import time
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, make_batch, write_csv
from codes.matrix_sources import get_matrix_source
from linear_kernel import HybridPlanner, NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16

DEFAULT_MATRIX_SOURCE = "galois_systematic_candidate"
DEFAULT_DENSITIES = (0.005, 0.05, 0.5)
DEFAULT_BATCH_SIZES = (1, 16, 64, 4096)
DEFAULT_FLIP_COUNTS = (1, 2, 4)
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 3
RNG_SEED = 20260708


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def _time_repeats(fn, repeats: int) -> list[float]:
    fn()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _make_flip_positions(
    rng: np.random.Generator,
    batch_size: int,
    component_n: int,
    flip_count: int,
) -> np.ndarray:
    return np.stack(
        [rng.choice(component_n, size=flip_count, replace=False) for _ in range(batch_size)],
        axis=0,
    ).astype(np.int64, copy=False)


def _apply_flips(x_batch: np.ndarray, flipped_positions: np.ndarray) -> np.ndarray:
    flipped = x_batch.copy()
    rows = np.repeat(np.arange(x_batch.shape[0]), flipped_positions.shape[1])
    cols = flipped_positions.reshape(-1)
    flipped[rows, cols] ^= 1
    return flipped


def _append_timing_row(
    rows: list[dict[str, Any]],
    *,
    matrix_source: str,
    workload_type: str,
    backend_or_method: str,
    batch_size: int,
    density: float,
    flip_count: int,
    block_width: int,
    samples: list[float],
    repeats: int,
    correctness_passed: bool,
) -> None:
    mean = statistics.fmean(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0.0
    rows.append(
        {
            "matrix_source": matrix_source,
            "workload_type": workload_type,
            "backend_or_method": backend_or_method,
            "batch_size": batch_size,
            "density": density,
            "flip_count": flip_count,
            "block_width": block_width,
            "total_runtime_s": mean,
            "latency_per_word_us": mean / batch_size * 1_000_000.0,
            "throughput_Mword_s": batch_size / mean / 1_000_000.0,
            "repeats": repeats,
            "mean": mean,
            "std": std,
            "correctness_passed": correctness_passed,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-source", default=DEFAULT_MATRIX_SOURCE)
    parser.add_argument("--densities", default=",".join(str(x) for x in DEFAULT_DENSITIES))
    parser.add_argument(
        "--batch-sizes",
        default=",".join(str(x) for x in DEFAULT_BATCH_SIZES),
    )
    parser.add_argument(
        "--flip-counts",
        default=",".join(str(x) for x in DEFAULT_FLIP_COUNTS),
    )
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = get_matrix_source(args.matrix_source)
    component_n, _ = matrix.shape
    naive = NaiveGF2Kernel(matrix)
    packed_block = PackedBlockLUTKernel(matrix, block_width=args.block_width)
    planner = HybridPlanner(matrix, block_width=args.block_width)
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, Any]] = []

    for density in _parse_float_list(args.densities):
        for batch_size in _parse_int_list(args.batch_sizes):
            x_batch = make_batch(rng, batch_size, density, n=component_n)
            expected = naive.apply_many(x_batch)
            expected_packed = pack_batch_bits_to_uint16(expected)
            packed_actual = packed_block.apply_many_packed(x_batch)
            planner_packed_actual = planner.apply_many_packed(x_batch)
            correctness_passed = bool(
                np.array_equal(packed_actual, expected_packed)
                and np.array_equal(planner_packed_actual, expected_packed)
            )
            if not correctness_passed:
                raise AssertionError("planner batch_syndrome correctness failed")

            methods = [
                ("Naive.apply_many", lambda x_batch=x_batch: naive.apply_many(x_batch)),
                (
                    "PackedBlockLUT.apply_many_packed",
                    lambda x_batch=x_batch: packed_block.apply_many_packed(x_batch),
                ),
                (
                    "HybridPlanner.apply_many_packed",
                    lambda x_batch=x_batch: planner.apply_many_packed(x_batch),
                ),
            ]
            for backend_or_method, fn in methods:
                _append_timing_row(
                    rows,
                    matrix_source=args.matrix_source,
                    workload_type="batch_syndrome",
                    backend_or_method=backend_or_method,
                    batch_size=batch_size,
                    density=density,
                    flip_count=0,
                    block_width=args.block_width,
                    samples=_time_repeats(fn, args.repeats),
                    repeats=args.repeats,
                    correctness_passed=correctness_passed,
                )

            old_syndromes = expected
            for flip_count in _parse_int_list(args.flip_counts):
                flipped_positions = _make_flip_positions(
                    rng,
                    batch_size,
                    component_n,
                    flip_count,
                )
                x_flipped = _apply_flips(x_batch, flipped_positions)
                expected_new = naive.apply_many(x_flipped)
                expected_new_packed = pack_batch_bits_to_uint16(expected_new)
                packed_block_new = packed_block.apply_many_packed(x_flipped)
                planner_updated = planner.update_many(old_syndromes, flipped_positions)
                update_correctness_passed = bool(
                    np.array_equal(packed_block_new, expected_new_packed)
                    and np.array_equal(planner_updated, expected_new)
                )
                if not update_correctness_passed:
                    raise AssertionError("planner event_update correctness failed")

                update_methods = [
                    (
                        "from_scratch.Naive.apply_many",
                        lambda x_flipped=x_flipped: naive.apply_many(x_flipped),
                    ),
                    (
                        "from_scratch.PackedBlockLUT.apply_many_packed",
                        lambda x_flipped=x_flipped: packed_block.apply_many_packed(
                            x_flipped
                        ),
                    ),
                    (
                        "HybridPlanner.update_many",
                        lambda old_syndromes=old_syndromes, flipped_positions=flipped_positions: planner.update_many(
                            old_syndromes,
                            flipped_positions,
                        ),
                    ),
                ]
                for backend_or_method, fn in update_methods:
                    _append_timing_row(
                        rows,
                        matrix_source=args.matrix_source,
                        workload_type="event_update",
                        backend_or_method=backend_or_method,
                        batch_size=batch_size,
                        density=density,
                        flip_count=flip_count,
                        block_width=args.block_width,
                        samples=_time_repeats(fn, args.repeats),
                        repeats=args.repeats,
                        correctness_passed=update_correctness_passed,
                    )

    output = RAW_DIR / "planner.csv"
    write_csv(output, rows)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
