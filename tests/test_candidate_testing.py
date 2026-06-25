"""Tests for candidate error-pattern testing helpers."""

from __future__ import annotations

import numpy as np
import pytest

from benchmarks import bench_candidate_testing
from benchmarks.bench_candidate_testing import evaluate_candidate_backends, run_candidate_testing_rows
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16
from workloads.candidate_patterns import make_chase_ii_patterns


def test_candidate_backends_match_naive_and_packed_reference() -> None:
    matrix = np.array(
        [
            [1, 0, 1],
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 1],
        ],
        dtype=np.uint8,
    )
    candidates = make_chase_ii_patterns(n=4, p_chase=2, positions=[0, 2])
    target = np.array([0, 0, 0], dtype=np.uint8)

    rows = evaluate_candidate_backends(
        matrix=matrix,
        candidates=candidates,
        target_syndrome=target,
        block_width=2,
        batch_size=4,
        repeats=1,
        preset="unit",
        code_profile="unit_profile",
        pattern_type="chase_ii_all",
        p_chase=2,
        candidate_weight=0,
    )

    assert {row["backend"] for row in rows} >= {
        "Naive.apply_many",
        "SparseXor.apply_many",
        "PackedBatch.apply_many",
        "PackedBlockLUT.apply_many_packed",
        "EventUpdate.from_zero",
        "HybridPlanner.apply_many",
        "HybridPlanner.apply_many_packed",
    }
    assert all(row["correctness_passed"] is True for row in rows)
    assert all("output_mode" in row for row in rows)
    assert all("selected_backend" in row for row in rows)
    assert all("selected_backend_reason" in row for row in rows)
    packed_planner = next(row for row in rows if row["backend"] == "HybridPlanner.apply_many_packed")
    unpacked_planner = next(row for row in rows if row["backend"] == "HybridPlanner.apply_many")
    assert packed_planner["output_mode"] == "packed"
    assert packed_planner["selected_backend"] == "PackedBlockLUTKernel"
    assert unpacked_planner["output_mode"] == "unpacked"
    assert unpacked_planner["selected_backend"]
    naive_syndromes = candidates @ matrix % 2
    expected_matches = int(np.all(naive_syndromes == target, axis=1).sum())
    assert {row["matches_found"] for row in rows} == {expected_matches}

    packed_row = next(row for row in rows if row["backend"] == "PackedBlockLUT.apply_many_packed")
    assert packed_row["packed_word_bits"] == 16
    np.testing.assert_array_equal(pack_batch_bits_to_uint16(naive_syndromes), packed_row["debug_packed_output"])


def test_candidate_known_hit_target_records_at_least_one_match() -> None:
    rows = run_candidate_testing_rows(
        preset="unit",
        code_profiles=("synthetic_bch_like_127_r14",),
        pattern_types=("fixed_weight",),
        p_chase_values=(3,),
        candidate_weights=(2,),
        candidate_counts=(8,),
        block_width=4,
        repeats=1,
        target_mode="known_hit",
    )

    assert rows
    assert {row["target_mode"] for row in rows} == {"known_hit"}
    assert all(int(row["matches_found"]) >= 1 for row in rows)
    assert len({row["matches_found"] for row in rows}) == 1


def test_candidate_zero_target_mode_is_still_available() -> None:
    rows = run_candidate_testing_rows(
        preset="unit",
        code_profiles=("synthetic_bch_like_127_r14",),
        pattern_types=("fixed_weight",),
        p_chase_values=(3,),
        candidate_weights=(1,),
        candidate_counts=(8,),
        block_width=4,
        repeats=1,
        target_mode="zero",
    )

    assert rows
    assert {row["target_mode"] for row in rows} == {"zero"}


def test_candidate_known_hit_allows_multiple_matching_candidates() -> None:
    matrix = np.zeros((4, 3), dtype=np.uint8)
    candidates = make_chase_ii_patterns(n=4, p_chase=2, positions=[0, 1])
    target = np.zeros(3, dtype=np.uint8)

    rows = evaluate_candidate_backends(
        matrix=matrix,
        candidates=candidates,
        target_syndrome=target,
        block_width=2,
        batch_size=4,
        repeats=1,
        preset="unit",
        code_profile="unit_zero_profile",
        pattern_type="chase_ii_all",
        p_chase=2,
        candidate_weight=0,
        target_mode="known_hit",
    )

    assert rows
    assert {row["matches_found"] for row in rows} == {candidates.shape[0]}
    assert all(row["correctness_passed"] is True for row in rows)


def test_candidate_benchmark_correctness_mismatch_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    matrix = np.array(
        [
            [1, 0],
            [0, 1],
            [1, 1],
        ],
        dtype=np.uint8,
    )
    candidates = make_chase_ii_patterns(n=3, p_chase=2, positions=[0, 1])
    target = candidates[1] @ matrix % 2

    def wrong_apply_many(self: object, x_batch: np.ndarray) -> np.ndarray:
        return np.ones((x_batch.shape[0], matrix.shape[1]), dtype=np.uint8)

    monkeypatch.setattr(
        bench_candidate_testing.PackedBatchGF2Kernel,
        "apply_many",
        wrong_apply_many,
    )

    with pytest.raises(AssertionError, match="correctness failed"):
        evaluate_candidate_backends(
            matrix=matrix,
            candidates=candidates,
            target_syndrome=target,
            block_width=2,
            batch_size=4,
            repeats=1,
            preset="unit",
            code_profile="unit_profile",
            pattern_type="chase_ii_all",
            p_chase=2,
            candidate_weight=0,
        )
