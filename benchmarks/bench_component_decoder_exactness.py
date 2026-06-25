"""Component decoder exactness benchmark using a bounded-distance LUT.

This benchmark checks syndrome-backend + BDD-LUT consistency only. It does not
implement BER simulation, a full BCH algebraic decoder, or any full outer code.
"""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from decoders.bdd_lut import BDDLUTDecoder
from linear_kernel import HybridPlanner, NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel

from ._common import RAW_DIR, ensure_result_dirs, time_repeats, write_csv

RNG_SEED = 20260724
DEFAULT_BLOCK_WIDTH = 8
LIGHTWEIGHT_CODE_PROFILES = ("bch_255_239_r16",)
FULL_CODE_PROFILES = ("bch_255_239_r16",)
DEFAULT_TEST_CASES = (
    "all_zero",
    "all_single_bit_errors",
    "sampled_double_bit_errors",
    "all_double_bit_errors",
    "sampled_triple_bit_errors",
    "random_error_batch",
    "random_received_batch",
)

COMPONENT_DECODER_FIELDNAMES = [
    "preset",
    "code_profile",
    "n",
    "r",
    "t",
    "test_case",
    "num_words",
    "double_error_coverage",
    "num_possible_double_errors",
    "error_weight",
    "syndrome_backend",
    "decoder_backend",
    "selected_backend",
    "selected_backend_reason",
    "decoded_word_equal",
    "correction_mask_equal",
    "status_equal",
    "exact_mismatch_count",
    "num_no_error",
    "num_corrected",
    "num_failure",
    "latency_per_word_us",
    "throughput_Mword_s",
    "mean",
    "std",
    "repeats",
    "correctness_passed",
    "notes",
]


@dataclass(frozen=True)
class ComponentDecoderCase:
    """One received-word batch for component decoder exactness checks."""

    name: str
    words: np.ndarray
    error_weight: str
    double_error_coverage: str = ""
    num_possible_double_errors: int = 0


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _parse_int(value: str | int | None, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, str):
        return int(value.strip())
    return int(value)


def _set_positions(n: int, positions: tuple[int, ...]) -> np.ndarray:
    word = np.zeros(n, dtype=np.uint8)
    if positions:
        word[np.array(positions, dtype=np.int64)] = 1
    return word


def _sample_pairs(n: int, count: int, rng: np.random.Generator) -> list[tuple[int, int]]:
    all_pairs = list(combinations(range(n), 2))
    if len(all_pairs) <= count:
        return all_pairs
    selected = rng.choice(len(all_pairs), size=count, replace=False)
    return [all_pairs[int(index)] for index in selected]


def _sample_triples(n: int, count: int, rng: np.random.Generator) -> list[tuple[int, int, int]]:
    max_total = n * (n - 1) * (n - 2) // 6
    count = min(count, max_total)
    triples: set[tuple[int, int, int]] = set()
    while len(triples) < count:
        triples.add(tuple(sorted(int(x) for x in rng.choice(n, size=3, replace=False))))
    return sorted(triples)


def _random_error_words(
    *,
    n: int,
    count: int,
    max_weight: int,
    rng: np.random.Generator,
) -> np.ndarray:
    words = np.zeros((count, n), dtype=np.uint8)
    for row in range(count):
        weight = int(rng.integers(0, max_weight + 1))
        if weight:
            words[row, rng.choice(n, size=min(weight, n), replace=False)] = 1
    return words


def make_component_decoder_cases(
    *,
    matrix: np.ndarray,
    preset: str,
    double_sample_size: int,
    random_batch_size: int,
    rng: np.random.Generator,
) -> list[ComponentDecoderCase]:
    """Create deterministic component decoder exactness test batches."""
    n, _ = matrix.shape
    num_possible_double_errors = n * (n - 1) // 2
    requested_double_count = 32385 if preset == "full" and n == 255 else double_sample_size
    double_count = min(requested_double_count, num_possible_double_errors)
    double_coverage = "full" if double_count == num_possible_double_errors else "sampled"
    double_case_name = (
        "all_double_bit_errors" if double_coverage == "full" else "sampled_double_bit_errors"
    )
    triple_count = 4096 if preset == "full" else min(random_batch_size, 2048)
    cases = [
        ComponentDecoderCase("all_zero", np.zeros((1, n), dtype=np.uint8), "0"),
        ComponentDecoderCase("all_single_bit_errors", np.eye(n, dtype=np.uint8), "1"),
        ComponentDecoderCase(
            double_case_name,
            np.stack([_set_positions(n, pair) for pair in _sample_pairs(n, double_count, rng)]),
            "2",
            double_coverage,
            num_possible_double_errors,
        ),
        ComponentDecoderCase(
            "sampled_triple_bit_errors",
            np.stack(
                [_set_positions(n, triple) for triple in _sample_triples(n, triple_count, rng)]
            ),
            "3",
        ),
        ComponentDecoderCase(
            "random_error_batch",
            _random_error_words(
                n=n,
                count=random_batch_size,
                max_weight=min(4, n),
                rng=rng,
            ),
            "mixed_0_to_4",
        ),
        ComponentDecoderCase(
            "random_received_batch",
            (rng.random((random_batch_size, n)) < 0.02).astype(np.uint8),
            "random_density_0.02",
        ),
    ]
    return cases


def _count_mismatches(reference: dict[str, np.ndarray], actual: dict[str, np.ndarray]) -> int:
    decoded = np.any(reference["corrected_words"] != actual["corrected_words"], axis=1)
    masks = np.any(reference["correction_masks"] != actual["correction_masks"], axis=1)
    statuses = reference["statuses"] != actual["statuses"]
    return int(np.count_nonzero(decoded | masks | statuses))


def _status_counts(statuses: np.ndarray) -> dict[str, int]:
    return {
        "num_no_error": int(np.count_nonzero(statuses == "no_error")),
        "num_corrected": int(np.count_nonzero(statuses == "corrected")),
        "num_failure": int(np.count_nonzero(statuses == "failure")),
    }


def _summary(samples: list[float], num_words: int) -> dict[str, float]:
    per_word = [sample / num_words for sample in samples]
    mean = statistics.fmean(per_word)
    std = statistics.stdev(per_word) if len(per_word) > 1 else 0.0
    return {
        "latency_per_word_us": mean * 1_000_000.0,
        "throughput_Mword_s": (1.0 / mean / 1_000_000.0) if mean > 0 else 0.0,
        "mean": statistics.fmean(samples),
        "std": statistics.stdev(samples) if len(samples) > 1 else 0.0,
    }


def _planner_selection(planner: HybridPlanner, matrix: np.ndarray, batch_size: int) -> tuple[str, str]:
    backend = planner.choose_backend(
        matrix,
        {"type": "batch", "batch_size": batch_size, "output_mode": "packed"},
    )
    return type(backend).__name__, "HybridPlanner batch packed-output rule"


def evaluate_component_decoder_case(
    *,
    matrix: np.ndarray,
    case: ComponentDecoderCase,
    preset: str,
    code_profile: str,
    block_width: int,
    repeats: int,
    t: int = 2,
) -> list[dict[str, Any]]:
    """Evaluate one case across syndrome backends and fail fast on mismatch."""
    n, r = matrix.shape
    decoder = BDDLUTDecoder(matrix, t=t)
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(matrix, block_width=block_width)
    planner = HybridPlanner(matrix, block_width=block_width)
    words = case.words

    reference = decoder.decode_words(words, syndrome_backend=naive)
    specs: list[tuple[str, object, str, str]] = [
        ("NaiveGF2Kernel.apply_many", naive, "NaiveGF2Kernel", "reference from-scratch"),
        (
            "PackedBatchGF2Kernel.apply_many",
            packed_batch,
            "PackedBatchGF2Kernel",
            "vectorized unpacked syndrome path",
        ),
        (
            "PackedBlockLUTKernel.apply_many_packed",
            packed_lut,
            "PackedBlockLUTKernel",
            "packed LUT syndrome path",
        ),
        (
            "HybridPlanner.apply_many_packed",
            planner,
            *_planner_selection(planner, matrix, words.shape[0]),
        ),
    ]

    rows: list[dict[str, Any]] = []
    for syndrome_backend, backend_obj, selected_backend, selected_reason in specs:
        actual = decoder.decode_words(words, syndrome_backend=backend_obj)
        decoded_equal = bool(np.array_equal(actual["corrected_words"], reference["corrected_words"]))
        mask_equal = bool(np.array_equal(actual["correction_masks"], reference["correction_masks"]))
        status_equal = bool(np.array_equal(actual["statuses"], reference["statuses"]))
        mismatch_count = _count_mismatches(reference, actual)
        if mismatch_count:
            raise AssertionError(
                "component decoder exactness mismatch: "
                f"{code_profile},{case.name},{syndrome_backend},mismatches={mismatch_count}"
            )
        fn: Callable[[], dict[str, np.ndarray]] = lambda backend_obj=backend_obj: decoder.decode_words(
            words,
            syndrome_backend=backend_obj,
        )
        samples = time_repeats(fn, repeats=repeats, warmups=1)
        rows.append(
            {
                "preset": preset,
                "code_profile": code_profile,
                "n": n,
                "r": r,
                "t": t,
                "test_case": case.name,
                "num_words": words.shape[0],
                "double_error_coverage": case.double_error_coverage,
                "num_possible_double_errors": case.num_possible_double_errors,
                "error_weight": case.error_weight,
                "syndrome_backend": syndrome_backend,
                "decoder_backend": "BDDLUTDecoder",
                "selected_backend": selected_backend,
                "selected_backend_reason": selected_reason,
                "decoded_word_equal": decoded_equal,
                "correction_mask_equal": mask_equal,
                "status_equal": status_equal,
                "exact_mismatch_count": mismatch_count,
                **_status_counts(actual["statuses"]),
                **_summary(samples, words.shape[0]),
                "repeats": repeats,
                "correctness_passed": True,
                "notes": "component BDD LUT exactness only; no BER; no full decoder",
            }
        )
    return rows


def run_component_decoder_exactness_rows(
    *,
    preset: str,
    code_profiles: tuple[str, ...],
    matrices: dict[str, np.ndarray] | None = None,
    test_cases: tuple[str, ...] = DEFAULT_TEST_CASES,
    double_sample_size: int = 4096,
    random_batch_size: int = 1024,
    repeats: int = 3,
    block_width: int = DEFAULT_BLOCK_WIDTH,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(RNG_SEED)
    matrices = matrices or {}
    wanted_cases = set(test_cases)
    for profile_name in code_profiles:
        if profile_name in matrices:
            matrix = np.asarray(matrices[profile_name], dtype=np.uint8) & 1
            code_profile_name = profile_name
        else:
            matrix = get_profile_matrix(profile_name)
            code_profile_name = get_code_profile(profile_name).profile_name
        cases = [
            case
            for case in make_component_decoder_cases(
                matrix=matrix,
                preset=preset,
                double_sample_size=double_sample_size,
                random_batch_size=random_batch_size,
                rng=rng,
            )
            if case.name in wanted_cases
        ]
        for case in cases:
            rows.extend(
                evaluate_component_decoder_case(
                    matrix=matrix,
                    case=case,
                    preset=preset,
                    code_profile=code_profile_name,
                    block_width=block_width,
                    repeats=repeats,
                )
            )
    return [{field: row.get(field, "") for field in COMPONENT_DECODER_FIELDNAMES} for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run component decoder exactness benchmark.")
    parser.add_argument("--preset", choices=("lightweight", "full"), default="lightweight")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--test-cases", default=None)
    parser.add_argument("--double-sample-size", type=int, default=None)
    parser.add_argument("--random-batch-size", type=int, default=None)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
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
    test_cases = _parse_str_list(args.test_cases) if args.test_cases else DEFAULT_TEST_CASES
    double_sample_size = _parse_int(args.double_sample_size, 4096 if preset == "lightweight" else 32385)
    random_batch_size = _parse_int(args.random_batch_size, 1024 if preset == "lightweight" else 4096)

    ensure_result_dirs()
    rows = run_component_decoder_exactness_rows(
        preset=preset,
        code_profiles=code_profiles,
        test_cases=test_cases,
        double_sample_size=double_sample_size,
        random_batch_size=random_batch_size,
        repeats=repeats,
        block_width=args.block_width,
    )
    output = RAW_DIR / "component_decoder_exactness.csv"
    write_csv(output, rows)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
