"""Candidate error-pattern syndrome benchmark.

This benchmark times candidate mask syndrome computation only. It does not
implement a Chase-Pyndiah, ORBGRAND, DEPT, BCH, eBCH, or OFEC decoder.
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Callable
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from linear_kernel import (
    EventUpdateKernel,
    HybridPlanner,
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    PackedBlockLUTKernel,
    SparseXorKernel,
)
from linear_kernel.matrix_utils import (
    pack_batch_bits_to_uint16,
    pack_batch_bits_to_uint32,
    pack_bits_to_uint16,
    pack_bits_to_uint32,
)
from workloads.candidate_patterns import make_chase_ii_patterns, make_fixed_weight_patterns

from ._common import RAW_DIR, ensure_result_dirs, time_repeats, write_csv

LIGHTWEIGHT_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_511_r32",
)
FULL_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_bch_like_127_r14",
    "synthetic_511_r32",
)
LIGHTWEIGHT_PATTERN_TYPES = ("chase_ii_all", "fixed_weight")
LIGHTWEIGHT_P_CHASE = (3, 5)
LIGHTWEIGHT_WEIGHTS = (1, 2, 4, 8)
LIGHTWEIGHT_COUNTS = (256, 4096)
FULL_P_CHASE = (3, 4, 5, 6)
FULL_WEIGHTS = (0, 1, 2, 3, 4, 8)
FULL_COUNTS = (256, 1024, 4096, 16384)
DEFAULT_BLOCK_WIDTH = 8
RNG_SEED = 20260722

CANDIDATE_FIELDNAMES = [
    "preset",
    "target_mode",
    "code_profile",
    "n",
    "r",
    "pattern_type",
    "p_chase",
    "candidate_weight",
    "candidate_count",
    "backend",
    "batch_size",
    "block_width",
    "packed_word_bits",
    "latency_per_candidate_us",
    "throughput_Mcandidate_s",
    "matches_found",
    "mean",
    "std",
    "repeats",
    "correctness_passed",
]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _packed_word_bits(r: int) -> int:
    return 16 if r <= 16 else 32


def _pack_batch(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _pack_vector(bits: np.ndarray) -> np.uint16 | np.uint32:
    if bits.shape[0] <= 16:
        return pack_bits_to_uint16(bits)
    return pack_bits_to_uint32(bits)


def make_target_syndrome(
    *,
    matrix: np.ndarray,
    candidates: np.ndarray,
    target_mode: str,
) -> np.ndarray:
    """Return the target syndrome used for candidate matching."""

    target_mode = target_mode.strip()
    if target_mode == "zero":
        return np.zeros(matrix.shape[1], dtype=np.uint8)
    if target_mode != "known_hit":
        raise ValueError("target_mode must be zero or known_hit")

    naive = NaiveGF2Kernel(matrix)
    syndromes = naive.apply_many(candidates)
    for syndrome in syndromes:
        if np.any(syndrome):
            return syndrome.copy()
    return syndromes[0].copy()


def _summary(samples: list[float], candidate_count: int) -> dict[str, float]:
    per_candidate = [sample / candidate_count for sample in samples]
    mean = statistics.fmean(per_candidate)
    std = statistics.stdev(per_candidate) if len(per_candidate) > 1 else 0.0
    return {
        "latency_per_candidate_us": mean * 1_000_000.0,
        "throughput_Mcandidate_s": (1.0 / mean / 1_000_000.0) if mean > 0 else 0.0,
        "mean": statistics.fmean(samples),
        "std": statistics.stdev(samples) if len(samples) > 1 else 0.0,
    }


def assert_outputs_match(
    backend: str,
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    context: str,
) -> None:
    if not np.array_equal(actual, expected):
        raise AssertionError(f"candidate testing correctness failed for {backend}: {context}")


def _event_update_from_zero(event_kernel: EventUpdateKernel, candidates: np.ndarray) -> np.ndarray:
    zero = np.zeros(event_kernel.r, dtype=np.uint8)
    return np.stack(
        [event_kernel.update(zero, np.flatnonzero(candidate)) for candidate in candidates],
        axis=0,
    )


def _matches_unpacked(syndromes: np.ndarray, target: np.ndarray) -> int:
    return int(np.all(syndromes == target, axis=1).sum())


def _matches_packed(packed: np.ndarray, target_packed: np.uint16 | np.uint32) -> int:
    return int(np.count_nonzero(packed == target_packed))


def evaluate_candidate_backends(
    *,
    matrix: np.ndarray,
    candidates: np.ndarray,
    target_syndrome: np.ndarray,
    block_width: int,
    batch_size: int,
    repeats: int,
    preset: str,
    code_profile: str,
    pattern_type: str,
    p_chase: int,
    candidate_weight: int,
    target_mode: str = "custom",
    include_debug: bool = True,
) -> list[dict[str, Any]]:
    """Evaluate all candidate-testing methods for one candidate matrix."""

    n, r = matrix.shape
    candidate_count = candidates.shape[0]
    packed_bits = _packed_word_bits(r)
    naive = NaiveGF2Kernel(matrix)
    sparse = SparseXorKernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=packed_bits)
    event_kernel = EventUpdateKernel(matrix)
    planner = HybridPlanner(matrix, block_width=block_width)

    expected = naive.apply_many(candidates)
    expected_packed = _pack_batch(expected)
    target_packed = _pack_vector(target_syndrome)
    context = f"{code_profile},{pattern_type},count={candidate_count}"

    specs: list[tuple[str, Callable[[], np.ndarray], np.ndarray, Callable[[np.ndarray], int]]] = [
        (
            "Naive.apply_many",
            lambda: naive.apply_many(candidates),
            expected,
            lambda actual: _matches_unpacked(actual, target_syndrome),
        ),
        (
            "SparseXor.apply_many",
            lambda: sparse.apply_many(candidates),
            expected,
            lambda actual: _matches_unpacked(actual, target_syndrome),
        ),
        (
            "PackedBatch.apply_many",
            lambda: packed_batch.apply_many(candidates),
            expected,
            lambda actual: _matches_unpacked(actual, target_syndrome),
        ),
        (
            "PackedBlockLUT.apply_many_packed",
            lambda: packed_lut.apply_many_packed(candidates),
            expected_packed,
            lambda actual: _matches_packed(actual, target_packed),
        ),
        (
            "EventUpdate.from_zero",
            lambda: _event_update_from_zero(event_kernel, candidates),
            expected,
            lambda actual: _matches_unpacked(actual, target_syndrome),
        ),
        (
            "HybridPlanner.apply_many_packed",
            lambda: planner.apply_many_packed(candidates),
            expected_packed,
            lambda actual: _matches_packed(actual, target_packed),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for backend, fn, expected_value, match_fn in specs:
        actual = fn()
        assert_outputs_match(backend, actual, expected_value, context=context)
        samples = time_repeats(fn, repeats=repeats, warmups=1)
        row = {
            "preset": preset,
            "target_mode": target_mode,
            "code_profile": code_profile,
            "n": n,
            "r": r,
            "pattern_type": pattern_type,
            "p_chase": p_chase,
            "candidate_weight": candidate_weight,
            "candidate_count": candidate_count,
            "backend": backend,
            "batch_size": batch_size,
            "block_width": block_width,
            "packed_word_bits": packed_bits,
            **_summary(samples, candidate_count),
            "matches_found": match_fn(actual),
            "repeats": repeats,
            "correctness_passed": True,
        }
        if include_debug and backend == "PackedBlockLUT.apply_many_packed":
            row["debug_packed_output"] = actual
        rows.append(row)
    expected_matches = {row["matches_found"] for row in rows}
    if len(expected_matches) != 1:
        raise AssertionError(f"candidate testing matches_found mismatch: {context}")
    return rows


def _candidate_sets(
    *,
    n: int,
    pattern_types: tuple[str, ...],
    p_chase_values: tuple[int, ...],
    candidate_weights: tuple[int, ...],
    candidate_counts: tuple[int, ...],
    seed: int,
) -> list[tuple[str, int, int, np.ndarray]]:
    sets: list[tuple[str, int, int, np.ndarray]] = []
    if "chase_ii_all" in pattern_types:
        for p_chase in p_chase_values:
            sets.append(
                (
                    "chase_ii_all",
                    p_chase,
                    0,
                    make_chase_ii_patterns(n=n, p_chase=p_chase),
                )
            )
    if "fixed_weight" in pattern_types:
        for weight in candidate_weights:
            for count in candidate_counts:
                sets.append(
                    (
                        "fixed_weight",
                        0,
                        weight,
                        make_fixed_weight_patterns(
                            n=n,
                            candidate_weight=weight,
                            candidate_count=count,
                            seed=seed + weight + count,
                        ),
                    )
                )
    return sets


def run_candidate_testing_rows(
    *,
    preset: str,
    code_profiles: tuple[str, ...],
    pattern_types: tuple[str, ...],
    p_chase_values: tuple[int, ...],
    candidate_weights: tuple[int, ...],
    candidate_counts: tuple[int, ...],
    block_width: int,
    repeats: int,
    target_mode: str = "known_hit",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile_name in code_profiles:
        profile = get_code_profile(profile_name)
        matrix = get_profile_matrix(profile_name)
        n, r = matrix.shape
        for pattern_type, p_chase, weight, candidates in _candidate_sets(
            n=n,
            pattern_types=pattern_types,
            p_chase_values=p_chase_values,
            candidate_weights=candidate_weights,
            candidate_counts=candidate_counts,
            seed=RNG_SEED + n + r,
        ):
            target = make_target_syndrome(
                matrix=matrix,
                candidates=candidates,
                target_mode=target_mode,
            )
            new_rows = evaluate_candidate_backends(
                matrix=matrix,
                candidates=candidates,
                target_syndrome=target,
                block_width=block_width,
                batch_size=candidates.shape[0],
                repeats=repeats,
                preset=preset,
                code_profile=profile.profile_name,
                pattern_type=pattern_type,
                p_chase=p_chase,
                candidate_weight=weight,
                target_mode=target_mode,
                include_debug=False,
            )
            if target_mode == "known_hit":
                matched = {int(row["matches_found"]) for row in new_rows}
                if len(matched) != 1 or next(iter(matched)) < 1:
                    raise AssertionError("known_hit target did not produce a backend-consistent match")
            rows.extend(new_rows)
    return [{field: row.get(field, "") for field in CANDIDATE_FIELDNAMES} for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run candidate error-pattern GF(2) benchmark.")
    parser.add_argument("--preset", choices=("lightweight", "full"), default="lightweight")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--pattern-types", default=None)
    parser.add_argument("--p-chase", default=None)
    parser.add_argument("--candidate-weights", default=None)
    parser.add_argument("--candidate-counts", default=None)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--target-mode", choices=("zero", "known_hit"), default="known_hit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preset = args.preset
    repeats = args.repeats if args.repeats is not None else (3 if preset == "lightweight" else 7)
    code_profiles = (
        _parse_str_list(args.code_profiles)
        if args.code_profiles
        else (LIGHTWEIGHT_CODE_PROFILES if preset == "lightweight" else FULL_CODE_PROFILES)
    )
    pattern_types = (
        _parse_str_list(args.pattern_types)
        if args.pattern_types
        else LIGHTWEIGHT_PATTERN_TYPES
    )
    p_chase_values = (
        _parse_int_list(args.p_chase)
        if args.p_chase
        else (LIGHTWEIGHT_P_CHASE if preset == "lightweight" else FULL_P_CHASE)
    )
    candidate_weights = (
        _parse_int_list(args.candidate_weights)
        if args.candidate_weights
        else (LIGHTWEIGHT_WEIGHTS if preset == "lightweight" else FULL_WEIGHTS)
    )
    candidate_counts = (
        _parse_int_list(args.candidate_counts)
        if args.candidate_counts
        else (LIGHTWEIGHT_COUNTS if preset == "lightweight" else FULL_COUNTS)
    )

    ensure_result_dirs()
    rows = run_candidate_testing_rows(
        preset=preset,
        code_profiles=code_profiles,
        pattern_types=pattern_types,
        p_chase_values=p_chase_values,
        candidate_weights=candidate_weights,
        candidate_counts=candidate_counts,
        block_width=args.block_width,
        repeats=repeats,
        target_mode=args.target_mode,
    )
    output = RAW_DIR / "candidate_testing.csv"
    write_csv(output, rows)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
