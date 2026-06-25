"""Trace-level product/staircase/oFEC-like component-kernel workloads.

This benchmark measures clean-room GF(2) kernel call patterns only. It does not
implement full product-code, staircase-code, OFEC, Chase-Pyndiah, BCH/eBCH
decoding, or BER simulation.
"""

from __future__ import annotations

import argparse
import statistics
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from linear_kernel import EventUpdateKernel, NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32
from workloads.candidate_patterns import make_fixed_weight_patterns
from workloads.optical_traces import TraceEvent, generate_trace

from ._common import RAW_DIR, ensure_result_dirs, make_batch, time_repeats, write_csv

LIGHTWEIGHT_WORKLOAD_TYPES = ("product_like", "staircase_like", "ofec_like")
LIGHTWEIGHT_CODE_PROFILES = ("bch_255_239_r16", "ebch_256_239_r17")
LIGHTWEIGHT_ITERATIONS = (1, 3)
LIGHTWEIGHT_NUM_BLOCKS = (8, 32)
LIGHTWEIGHT_WINDOW_LEN = (4, 8)
FULL_ITERATIONS = (1, 3, 5)
FULL_NUM_BLOCKS = (8, 32, 128)
FULL_WINDOW_LEN = (4, 8, 16)
DEFAULT_DENSITY = 0.05
DEFAULT_BATCH_SIZE = 64
DEFAULT_BLOCK_WIDTH = 8
DEFAULT_MAX_CANDIDATE_TESTS_PER_EVENT = 256
RNG_SEED = 20260723

OPTICAL_FIELDNAMES = [
    "preset",
    "workload_type",
    "code_profile",
    "n",
    "r",
    "num_blocks",
    "window_len",
    "num_iterations_or_steps",
    "num_syndrome_calls",
    "num_candidate_tests",
    "num_executed_candidate_tests",
    "num_event_updates",
    "backend_or_method",
    "block_width",
    "batch_size",
    "density",
    "total_runtime_s",
    "latency_per_component_us",
    "throughput_Mcomponent_s",
    "mean",
    "std",
    "repeats",
    "correctness_passed",
    "notes",
]

OPTICAL_BREAKDOWN_FIELDNAMES = [
    "preset",
    "workload_type",
    "code_profile",
    "task_kind",
    "backend_or_method",
    "num_units",
    "unit_type",
    "total_runtime_s",
    "latency_per_unit_us",
    "throughput_Munit_s",
    "correctness_passed",
    "notes",
]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_float(value: str) -> float:
    return float(value.strip())


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _pack_batch(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _make_flip_positions(
    rng: np.random.Generator,
    batch_size: int,
    n: int,
    flip_count: int,
) -> np.ndarray:
    return np.stack(
        [rng.choice(n, size=flip_count, replace=False) for _ in range(batch_size)],
        axis=0,
    ).astype(np.int64, copy=False)


def _apply_flips(x_batch: np.ndarray, flip_positions: np.ndarray) -> np.ndarray:
    flipped = x_batch.copy()
    rows = np.repeat(np.arange(x_batch.shape[0]), flip_positions.shape[1])
    cols = flip_positions.reshape(-1)
    flipped[rows, cols] ^= 1
    return flipped


def _event_component_count(event: TraceEvent, batch_size: int) -> int:
    return max(1, min(event.component_count, batch_size))


def _prepare_tasks(
    *,
    events: tuple[TraceEvent, ...],
    n: int,
    density: float,
    batch_size: int,
    rng: np.random.Generator,
    naive: NaiveGF2Kernel,
) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        count = _event_component_count(event, batch_size)
        if event.event_type.startswith("candidate_test"):
            candidate_tests = max(1, event.executed_candidate_tests)
            candidates = make_fixed_weight_patterns(
                n=n,
                candidate_weight=2,
                candidate_count=candidate_tests,
                seed=RNG_SEED + index + n,
            )
            expected = naive.apply_many(candidates)
            tasks.append(
                {
                    "kind": "candidate_test",
                    "event_type": event.event_type,
                    "input": candidates,
                    "expected": expected,
                    "expected_packed": _pack_batch(expected),
                    "component_count": event.component_count,
                    "num_units": candidates.shape[0],
                    "unit_type": "candidate",
                    "intended_candidate_tests": event.intended_candidate_tests,
                    "executed_candidate_tests": event.executed_candidate_tests,
                }
            )
        elif event.event_type.startswith("event_update"):
            x_batch = make_batch(rng, count, density, n=n)
            old = naive.apply_many(x_batch)
            flips = _make_flip_positions(rng, count, n, max(1, event.flip_count))
            flipped = _apply_flips(x_batch, flips)
            expected = naive.apply_many(flipped)
            tasks.append(
                {
                    "kind": "event_update",
                    "event_type": event.event_type,
                    "input": flipped,
                    "old": old,
                    "flips": flips,
                    "expected": expected,
                    "expected_packed": _pack_batch(expected),
                    "component_count": count,
                    "num_units": count,
                    "unit_type": "update",
                }
            )
        else:
            x_batch = make_batch(rng, count, density, n=n)
            expected = naive.apply_many(x_batch)
            tasks.append(
                {
                    "kind": "syndrome",
                    "event_type": event.event_type,
                    "input": x_batch,
                    "expected": expected,
                    "expected_packed": _pack_batch(expected),
                    "component_count": count,
                    "num_units": count,
                    "unit_type": "component",
                }
            )
    return tasks


def _assert_task_correct(
    method: str,
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    context: str,
) -> None:
    if not np.array_equal(actual, expected):
        raise AssertionError(f"optical workload correctness failed for {method}: {context}")


def _run_method(
    method: str,
    tasks: list[dict[str, Any]],
    *,
    naive: NaiveGF2Kernel,
    packed_batch: PackedBatchGF2Kernel,
    packed_lut: PackedBlockLUTKernel,
    event_kernel: EventUpdateKernel,
    check: bool,
    context: str,
) -> None:
    for task in tasks:
        if method == "Naive.apply_many":
            actual = naive.apply_many(task["input"])
            if check:
                _assert_task_correct(method, actual, task["expected"], context=context)
        elif method == "PackedBatch.apply_many":
            actual = packed_batch.apply_many(task["input"])
            if check:
                _assert_task_correct(method, actual, task["expected"], context=context)
        elif method == "PackedBlockLUT.apply_many_packed":
            actual = packed_lut.apply_many_packed(task["input"])
            if check:
                _assert_task_correct(method, actual, task["expected_packed"], context=context)
        elif method == "EventUpdate.integrated":
            if task["kind"] == "event_update":
                actual = event_kernel.update_many(task["old"], task["flips"])
            else:
                actual = naive.apply_many(task["input"])
            if check:
                _assert_task_correct(method, actual, task["expected"], context=context)
        else:
            raise ValueError(f"unknown method: {method}")


def evaluate_optical_workload(
    *,
    workload_type: str,
    code_profile: str,
    num_blocks: int,
    window_len: int,
    num_iterations_or_steps: int,
    density: float,
    batch_size: int,
    block_width: int,
    repeats: int,
    preset: str,
    max_candidate_tests_per_event: int | None = None,
) -> list[dict[str, Any]]:
    aggregate_rows, _ = evaluate_optical_workload_with_breakdown(
        workload_type=workload_type,
        code_profile=code_profile,
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_iterations_or_steps,
        density=density,
        batch_size=batch_size,
        block_width=block_width,
        repeats=repeats,
        preset=preset,
        max_candidate_tests_per_event=max_candidate_tests_per_event,
    )
    return aggregate_rows


def evaluate_optical_workload_with_breakdown(
    *,
    workload_type: str,
    code_profile: str,
    num_blocks: int,
    window_len: int,
    num_iterations_or_steps: int,
    density: float,
    batch_size: int,
    block_width: int,
    repeats: int,
    preset: str,
    max_candidate_tests_per_event: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    profile = get_code_profile(code_profile)
    matrix = get_profile_matrix(code_profile)
    n, r = matrix.shape
    trace = generate_trace(
        workload_type=workload_type,
        profile=profile,
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_iterations_or_steps,
        max_candidate_tests_per_event=max_candidate_tests_per_event,
    )
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(matrix, block_width=block_width)
    event_kernel = EventUpdateKernel(matrix)
    rng = np.random.default_rng(RNG_SEED + n + r + num_blocks + window_len)
    tasks = _prepare_tasks(
        events=trace.events,
        n=n,
        density=density,
        batch_size=batch_size,
        rng=rng,
        naive=naive,
    )
    total_units = max(1, sum(task["num_units"] for task in tasks))
    methods = (
        "Naive.apply_many",
        "PackedBatch.apply_many",
        "PackedBlockLUT.apply_many_packed",
        "EventUpdate.integrated",
    )
    rows: list[dict[str, Any]] = []
    breakdown_rows: list[dict[str, Any]] = []
    context = f"{workload_type},{code_profile},blocks={num_blocks},window={window_len}"
    for method in methods:
        _run_method(
            method,
            tasks,
            naive=naive,
            packed_batch=packed_batch,
            packed_lut=packed_lut,
            event_kernel=event_kernel,
            check=True,
            context=context,
        )
        fn = lambda method=method: _run_method(
            method,
            tasks,
            naive=naive,
            packed_batch=packed_batch,
            packed_lut=packed_lut,
            event_kernel=event_kernel,
            check=False,
            context=context,
        )
        samples = time_repeats(fn, repeats=repeats, warmups=1)
        mean = statistics.fmean(samples)
        std = statistics.stdev(samples) if len(samples) > 1 else 0.0
        rows.append(
            {
                "preset": preset,
                "workload_type": workload_type,
                "code_profile": code_profile,
                "n": n,
                "r": r,
                "num_blocks": num_blocks,
                "window_len": window_len,
                "num_iterations_or_steps": num_iterations_or_steps,
                "num_syndrome_calls": trace.num_syndrome_calls,
                "num_candidate_tests": trace.num_candidate_tests,
                "num_executed_candidate_tests": trace.num_executed_candidate_tests,
                "num_event_updates": trace.num_event_updates,
                "backend_or_method": method,
                "block_width": block_width,
                "batch_size": batch_size,
                "density": density,
                "total_runtime_s": mean,
                "latency_per_component_us": mean / total_units * 1_000_000.0,
                "throughput_Mcomponent_s": total_units / mean / 1_000_000.0,
                "mean": mean,
                "std": std,
                "repeats": repeats,
                "correctness_passed": True,
                "notes": "trace-level workload only; no BER; no full decoder",
            }
        )
        for task_kind in ("syndrome", "candidate_test", "event_update"):
            selected_tasks = [task for task in tasks if task["kind"] == task_kind]
            if not selected_tasks:
                continue
            _run_method(
                method,
                selected_tasks,
                naive=naive,
                packed_batch=packed_batch,
                packed_lut=packed_lut,
                event_kernel=event_kernel,
                check=True,
                context=f"{context},{task_kind}",
            )
            task_fn = lambda method=method, selected_tasks=selected_tasks: _run_method(
                method,
                selected_tasks,
                naive=naive,
                packed_batch=packed_batch,
                packed_lut=packed_lut,
                event_kernel=event_kernel,
                check=False,
                context=f"{context},{task_kind}",
            )
            task_samples = time_repeats(task_fn, repeats=repeats, warmups=1)
            task_mean = statistics.fmean(task_samples)
            num_units = max(1, sum(int(task["num_units"]) for task in selected_tasks))
            unit_type = selected_tasks[0]["unit_type"]
            breakdown_rows.append(
                {
                    "preset": preset,
                    "workload_type": workload_type,
                    "code_profile": code_profile,
                    "task_kind": task_kind,
                    "backend_or_method": method,
                    "num_units": num_units,
                    "unit_type": unit_type,
                    "total_runtime_s": task_mean,
                    "latency_per_unit_us": task_mean / num_units * 1_000_000.0,
                    "throughput_Munit_s": num_units / task_mean / 1_000_000.0,
                    "correctness_passed": True,
                    "notes": "trace-level task breakdown; no BER; no full decoder",
                }
            )
    return rows, breakdown_rows


def run_optical_workload_rows(
    *,
    preset: str,
    workload_types: tuple[str, ...],
    code_profiles: tuple[str, ...],
    num_blocks_values: tuple[int, ...],
    window_len_values: tuple[int, ...],
    iteration_values: tuple[int, ...],
    density: float,
    batch_size: int,
    block_width: int,
    repeats: int,
    max_candidate_tests_per_event: int | None = DEFAULT_MAX_CANDIDATE_TESTS_PER_EVENT,
) -> list[dict[str, Any]]:
    rows, _ = run_optical_workload_tables(
        preset=preset,
        workload_types=workload_types,
        code_profiles=code_profiles,
        num_blocks_values=num_blocks_values,
        window_len_values=window_len_values,
        iteration_values=iteration_values,
        density=density,
        batch_size=batch_size,
        block_width=block_width,
        repeats=repeats,
        max_candidate_tests_per_event=max_candidate_tests_per_event,
    )
    return rows


def run_optical_workload_tables(
    *,
    preset: str,
    workload_types: tuple[str, ...],
    code_profiles: tuple[str, ...],
    num_blocks_values: tuple[int, ...],
    window_len_values: tuple[int, ...],
    iteration_values: tuple[int, ...],
    density: float,
    batch_size: int,
    block_width: int,
    repeats: int,
    max_candidate_tests_per_event: int | None = DEFAULT_MAX_CANDIDATE_TESTS_PER_EVENT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    breakdown_rows: list[dict[str, Any]] = []
    for workload_type in workload_types:
        for code_profile in code_profiles:
            for num_blocks in num_blocks_values:
                for window_len in window_len_values:
                    for iteration_count in iteration_values:
                        try:
                            new_rows, new_breakdown_rows = evaluate_optical_workload_with_breakdown(
                                workload_type=workload_type,
                                code_profile=code_profile,
                                num_blocks=num_blocks,
                                window_len=window_len,
                                num_iterations_or_steps=iteration_count,
                                density=density,
                                batch_size=batch_size,
                                block_width=block_width,
                                repeats=repeats,
                                preset=preset,
                                max_candidate_tests_per_event=max_candidate_tests_per_event,
                            )
                        except ValueError as exc:
                            if workload_type == "staircase_like" and "even" in str(exc):
                                print(f"skipped {workload_type}/{code_profile}: {exc}")
                                continue
                            raise
                        rows.extend(new_rows)
                        breakdown_rows.extend(new_breakdown_rows)
    return (
        [{field: row.get(field, "") for field in OPTICAL_FIELDNAMES} for row in rows],
        [
            {field: row.get(field, "") for field in OPTICAL_BREAKDOWN_FIELDNAMES}
            for row in breakdown_rows
        ],
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run trace-level optical workload benchmark.")
    parser.add_argument("--preset", choices=("lightweight", "full"), default="lightweight")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--workload-types", default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--num-blocks", default=None)
    parser.add_argument("--window-len", default=None)
    parser.add_argument("--iterations", default=None)
    parser.add_argument("--density", default=str(DEFAULT_DENSITY))
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument(
        "--max-candidate-tests-per-event",
        type=int,
        default=DEFAULT_MAX_CANDIDATE_TESTS_PER_EVENT,
        help="Cap executed candidate-test masks per trace event; records intended and executed counts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preset = args.preset
    repeats = args.repeats if args.repeats is not None else (3 if preset == "lightweight" else 7)
    workload_types = (
        _parse_str_list(args.workload_types)
        if args.workload_types
        else LIGHTWEIGHT_WORKLOAD_TYPES
    )
    code_profiles = (
        _parse_str_list(args.code_profiles)
        if args.code_profiles
        else LIGHTWEIGHT_CODE_PROFILES
    )
    num_blocks_values = (
        _parse_int_list(args.num_blocks)
        if args.num_blocks
        else (LIGHTWEIGHT_NUM_BLOCKS if preset == "lightweight" else FULL_NUM_BLOCKS)
    )
    window_len_values = (
        _parse_int_list(args.window_len)
        if args.window_len
        else (LIGHTWEIGHT_WINDOW_LEN if preset == "lightweight" else FULL_WINDOW_LEN)
    )
    iteration_values = (
        _parse_int_list(args.iterations)
        if args.iterations
        else (LIGHTWEIGHT_ITERATIONS if preset == "lightweight" else FULL_ITERATIONS)
    )

    ensure_result_dirs()
    rows, breakdown_rows = run_optical_workload_tables(
        preset=preset,
        workload_types=workload_types,
        code_profiles=code_profiles,
        num_blocks_values=num_blocks_values,
        window_len_values=window_len_values,
        iteration_values=iteration_values,
        density=_parse_float(args.density),
        batch_size=args.batch_size,
        block_width=args.block_width,
        repeats=repeats,
        max_candidate_tests_per_event=args.max_candidate_tests_per_event,
    )
    output = RAW_DIR / "optical_workloads.csv"
    write_csv(output, rows)
    print(f"wrote {output}")
    breakdown_output = RAW_DIR / "optical_workload_breakdown.csv"
    write_csv(breakdown_output, breakdown_rows)
    print(f"wrote {breakdown_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
