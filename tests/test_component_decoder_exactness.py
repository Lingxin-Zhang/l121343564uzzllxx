"""Tests for component decoder exactness benchmark helpers."""

from __future__ import annotations

import numpy as np

from benchmarks.bench_component_decoder_exactness import (
    COMPONENT_DECODER_FIELDNAMES,
    make_component_decoder_cases,
    run_component_decoder_exactness_rows,
)


def test_component_decoder_exactness_backends_match_on_small_profile() -> None:
    matrix = np.eye(6, dtype=np.uint8)
    rows = run_component_decoder_exactness_rows(
        preset="unit",
        code_profiles=("unit_identity",),
        matrices={"unit_identity": matrix},
        test_cases=("all_zero", "all_single_bit_errors", "sampled_double_bit_errors"),
        double_sample_size=8,
        random_batch_size=8,
        repeats=1,
        block_width=2,
    )

    assert rows
    assert {row["test_case"] for row in rows} == {
        "all_zero",
        "all_single_bit_errors",
        "sampled_double_bit_errors",
    }
    double_rows = [row for row in rows if row["test_case"] == "sampled_double_bit_errors"]
    assert double_rows
    assert {row["double_error_coverage"] for row in double_rows} == {"sampled"}
    assert {row["num_possible_double_errors"] for row in double_rows} == {15}
    assert {row["num_words"] for row in double_rows} == {8}
    assert {row["syndrome_backend"] for row in rows} >= {
        "NaiveGF2Kernel.apply_many",
        "PackedBatchGF2Kernel.apply_many",
        "PackedBlockLUTKernel.apply_many_packed",
        "HybridPlanner.apply_many_packed",
    }
    assert all(row["decoded_word_equal"] is True for row in rows)
    assert all(row["correction_mask_equal"] is True for row in rows)
    assert all(row["status_equal"] is True for row in rows)
    assert all(row["exact_mismatch_count"] == 0 for row in rows)
    assert all(row["correctness_passed"] is True for row in rows)
    assert all(set(COMPONENT_DECODER_FIELDNAMES) >= set(row) for row in rows)


def test_component_decoder_case_factory_includes_required_cases() -> None:
    matrix = np.eye(6, dtype=np.uint8)
    cases = make_component_decoder_cases(
        matrix=matrix,
        preset="unit",
        double_sample_size=8,
        random_batch_size=8,
        rng=np.random.default_rng(123),
    )

    names = {case.name for case in cases}
    assert {
        "all_zero",
        "all_single_bit_errors",
        "sampled_double_bit_errors",
        "sampled_triple_bit_errors",
        "random_error_batch",
        "random_received_batch",
    } <= names
    sampled_double = next(case for case in cases if case.name == "sampled_double_bit_errors")
    assert sampled_double.double_error_coverage == "sampled"
    assert sampled_double.num_possible_double_errors == 15
    assert all(case.words.dtype == np.uint8 for case in cases)


def test_component_decoder_full_double_case_is_named_all_only_when_fully_enumerated() -> None:
    matrix = np.eye(6, dtype=np.uint8)
    cases = make_component_decoder_cases(
        matrix=matrix,
        preset="full",
        double_sample_size=15,
        random_batch_size=8,
        rng=np.random.default_rng(123),
    )

    all_double = next(case for case in cases if case.name == "all_double_bit_errors")
    assert all_double.double_error_coverage == "full"
    assert all_double.num_possible_double_errors == 15
    assert all_double.words.shape[0] == 15
