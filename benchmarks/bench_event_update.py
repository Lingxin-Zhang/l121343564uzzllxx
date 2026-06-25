"""Benchmark event-driven syndrome updates after sparse bit flips."""

from __future__ import annotations

import argparse
import statistics
import time
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, make_batch, write_csv
from codes.matrix_sources import get_matrix_source
from linear_kernel import EventUpdateKernel, NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16

DEFAULT_MATRIX_SOURCE = "galois_systematic_candidate"
DEFAULT_BATCH_SIZE = 4096
DEFAULT_FLIP_COUNTS = (1, 2, 4, 8)
DEFAULT_ITERATIONS = (1, 5, 10)
DEFAULT_DENSITY = 0.05
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_REPEATS = 3
RNG_SEED = 20260707


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _make_flip_positions(
    rng: np.random.Generator,
    batch_size: int,
    component_n: int,
    flip_count: int,
) -> np.ndarray:
    return np.stack(
        [
            rng.choice(component_n, size=flip_count, replace=False)
            for _ in range(batch_size)
        ],
        axis=0,
    ).astype(np.int64, copy=False)


def _apply_flips(x_batch: np.ndarray, flip_positions: np.ndarray) -> np.ndarray:
    flipped = x_batch.copy()
    row_index = np.repeat(np.arange(x_batch.shape[0]), flip_positions.shape[1])
    col_index = flip_positions.reshape(-1)
    flipped[row_index, col_index] ^= 1
    return flipped


def _apply_event_updates(
    event_kernel: EventUpdateKernel,
    old_syndromes: np.ndarray,
    flip_positions: np.ndarray,
) -> np.ndarray:
    return np.stack(
        [
            event_kernel.update(current_value, positions)
            for current_value, positions in zip(old_syndromes, flip_positions, strict=True)
        ],
        axis=0,
    )


def check_event_update_correctness(
    matrix_source: str,
    batch_size: int,
    flip_count: int,
    density: float,
    block_width: int,
) -> bool:
    matrix = get_matrix_source(matrix_source)
    component_n, _ = matrix.shape
    rng = np.random.default_rng(RNG_SEED + flip_count + batch_size)
    x_batch = make_batch(rng, batch_size, density, n=component_n)
    flip_positions = _make_flip_positions(rng, batch_size, component_n, flip_count)
    x_flipped = _apply_flips(x_batch, flip_positions)

    naive = NaiveGF2Kernel(matrix)
    event_kernel = EventUpdateKernel(matrix)
    old_syndromes = naive.apply_many(x_batch)
    expected = naive.apply_many(x_flipped)
    actual = _apply_event_updates(event_kernel, old_syndromes, flip_positions)
    if not np.array_equal(actual, expected):
        raise AssertionError("EventUpdateKernel output disagrees with from-scratch")

    packed_block = PackedBlockLUTKernel(matrix, block_width=block_width)
    expected_packed = pack_batch_bits_to_uint16(expected)
    actual_packed = packed_block.apply_many_packed(x_flipped)
    if not np.array_equal(actual_packed, expected_packed):
        raise AssertionError("PackedBlockLUT from-scratch output disagrees with Naive")
    return True


def _run_from_scratch(
    x_flipped: np.ndarray,
    iterations: int,
    packed_block: PackedBlockLUTKernel,
) -> None:
    for _ in range(iterations):
        packed_block.apply_many_packed(x_flipped)


def _run_event_update(
    old_syndromes: np.ndarray,
    flip_positions: np.ndarray,
    iterations: int,
    event_kernel: EventUpdateKernel,
) -> None:
    for _ in range(iterations):
        _apply_event_updates(event_kernel, old_syndromes, flip_positions)


def _time_repeats(fn, repeats: int) -> list[float]:
    fn()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-source", default=DEFAULT_MATRIX_SOURCE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--flip-counts",
        default=",".join(str(x) for x in DEFAULT_FLIP_COUNTS),
    )
    parser.add_argument("--iterations", default=",".join(str(x) for x in DEFAULT_ITERATIONS))
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    args = parser.parse_args()

    ensure_result_dirs()
    matrix = get_matrix_source(args.matrix_source)
    component_n, output_r = matrix.shape
    rng = np.random.default_rng(RNG_SEED)
    x_batch = make_batch(rng, args.batch_size, args.density, n=component_n)

    naive = NaiveGF2Kernel(matrix)
    event_kernel = EventUpdateKernel(matrix)
    packed_block = PackedBlockLUTKernel(matrix, block_width=args.block_width)
    old_syndromes = naive.apply_many(x_batch)
    rows: list[dict[str, Any]] = []

    for flip_count in _parse_int_list(args.flip_counts):
        flip_positions = _make_flip_positions(
            rng,
            args.batch_size,
            component_n,
            flip_count,
        )
        x_flipped = _apply_flips(x_batch, flip_positions)
        expected = naive.apply_many(x_flipped)
        expected_packed = pack_batch_bits_to_uint16(expected)
        actual_update = _apply_event_updates(event_kernel, old_syndromes, flip_positions)
        actual_from_scratch = packed_block.apply_many_packed(x_flipped)
        correctness_passed = bool(
            np.array_equal(actual_update, expected)
            and np.array_equal(actual_from_scratch, expected_packed)
        )
        if not correctness_passed:
            raise AssertionError(f"event-update correctness failed for flip_count={flip_count}")

        for iterations in _parse_int_list(args.iterations):
            updates = args.batch_size * iterations
            methods = [
                (
                    "from_scratch.PackedBlockLUT.apply_many_packed",
                    lambda iterations=iterations, x_flipped=x_flipped: _run_from_scratch(
                        x_flipped,
                        iterations,
                        packed_block,
                    ),
                ),
                (
                    "event_update.EventUpdateKernel.update",
                    lambda iterations=iterations, flip_positions=flip_positions: _run_event_update(
                        old_syndromes,
                        flip_positions,
                        iterations,
                        event_kernel,
                    ),
                ),
            ]
            for method_name, fn in methods:
                samples = _time_repeats(fn, args.repeats)
                mean = statistics.fmean(samples)
                std = statistics.stdev(samples) if len(samples) > 1 else 0.0
                rows.append(
                    {
                        "matrix_source": args.matrix_source,
                        "method": method_name,
                        "component_n": component_n,
                        "output_r": output_r,
                        "batch_size": args.batch_size,
                        "flip_count": flip_count,
                        "iterations": iterations,
                        "total_runtime_s": mean,
                        "latency_per_word_us": mean / updates * 1_000_000.0,
                        "throughput_Mupdate_s": updates / mean / 1_000_000.0,
                        "repeats": args.repeats,
                        "mean": mean,
                        "std": std,
                        "correctness_passed": correctness_passed,
                    }
                )

    output = RAW_DIR / "event_update.csv"
    write_csv(output, rows)
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
