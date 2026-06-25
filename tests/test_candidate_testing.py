"""Tests for candidate error-pattern testing helpers."""

from __future__ import annotations

import numpy as np

from benchmarks.bench_candidate_testing import evaluate_candidate_backends
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
    }
    assert all(row["correctness_passed"] is True for row in rows)
    naive_syndromes = candidates @ matrix % 2
    expected_matches = int(np.all(naive_syndromes == target, axis=1).sum())
    assert {row["matches_found"] for row in rows} == {expected_matches}

    packed_row = next(row for row in rows if row["backend"] == "PackedBlockLUT.apply_many_packed")
    assert packed_row["packed_word_bits"] == 16
    np.testing.assert_array_equal(pack_batch_bits_to_uint16(naive_syndromes), packed_row["debug_packed_output"])
