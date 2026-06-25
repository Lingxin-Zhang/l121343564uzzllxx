"""Tests for bounded-distance decoder LUT helpers."""

from __future__ import annotations

import numpy as np
import pytest

from decoders.bdd_lut import BDDLUTDecoder


def _identity_matrix(width: int = 4) -> np.ndarray:
    return np.eye(width, dtype=np.uint8)


def test_bdd_lut_zero_syndrome_is_no_error() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)

    result = decoder.decode_syndrome(np.zeros(4, dtype=np.uint8))

    assert result.status == "no_error"
    assert result.correction_weight == 0
    assert result.syndrome_packed == 0
    np.testing.assert_array_equal(result.correction_mask, np.zeros(4, dtype=np.uint8))


def test_bdd_lut_all_single_bit_syndromes_decode_to_single_correction() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)

    for position in range(4):
        syndrome = np.zeros(4, dtype=np.uint8)
        syndrome[position] = 1
        result = decoder.decode_syndrome(syndrome)

        expected = np.zeros(4, dtype=np.uint8)
        expected[position] = 1
        assert result.status == "corrected"
        assert result.correction_weight == 1
        np.testing.assert_array_equal(result.correction_mask, expected)


def test_bdd_lut_sampled_double_bit_syndromes_decode_to_double_correction() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)

    for i, j in ((0, 1), (0, 3), (2, 3)):
        syndrome = np.zeros(4, dtype=np.uint8)
        syndrome[[i, j]] = 1
        result = decoder.decode_syndrome(syndrome)

        expected = np.zeros(4, dtype=np.uint8)
        expected[[i, j]] = 1
        assert result.status == "corrected"
        assert result.correction_weight == 2
        np.testing.assert_array_equal(result.correction_mask, expected)


def test_bdd_lut_unknown_syndrome_is_failure() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)

    result = decoder.decode_syndrome(np.ones(4, dtype=np.uint8))

    assert result.status == "failure"
    assert result.correction_weight == 0
    np.testing.assert_array_equal(result.correction_mask, np.zeros(4, dtype=np.uint8))


def test_bdd_lut_strict_collision_check_detects_conflicts() -> None:
    matrix = np.array(
        [
            [1, 0, 0],
            [1, 0, 0],
            [0, 1, 0],
        ],
        dtype=np.uint8,
    )

    with pytest.raises(ValueError, match="collision"):
        BDDLUTDecoder(matrix, t=2, strict_collision_check=True)

    decoder = BDDLUTDecoder(matrix, t=2, strict_collision_check=False)
    assert decoder.collision_count > 0


def test_bdd_lut_batch_decode_matches_individual_decode() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)
    syndromes = np.array(
        [
            [0, 0, 0, 0],
            [1, 0, 0, 0],
            [1, 0, 1, 0],
            [1, 1, 1, 1],
        ],
        dtype=np.uint8,
    )

    batch = decoder.decode_syndromes(syndromes)
    individual = [decoder.decode_syndrome(syndrome) for syndrome in syndromes]

    np.testing.assert_array_equal(
        batch["correction_masks"],
        np.stack([result.correction_mask for result in individual]),
    )
    np.testing.assert_array_equal(
        batch["statuses"],
        np.array([result.status for result in individual], dtype=object),
    )
    np.testing.assert_array_equal(
        batch["correction_weights"],
        np.array([result.correction_weight for result in individual], dtype=np.uint8),
    )


def test_bdd_lut_decode_word_and_words_apply_corrections_only_when_not_failure() -> None:
    decoder = BDDLUTDecoder(_identity_matrix(), t=2)
    words = np.array(
        [
            [1, 0, 0, 0],
            [1, 0, 1, 0],
            [1, 1, 1, 1],
        ],
        dtype=np.uint8,
    )

    batch = decoder.decode_words(words)

    np.testing.assert_array_equal(batch["corrected_words"][0], np.zeros(4, dtype=np.uint8))
    np.testing.assert_array_equal(batch["corrected_words"][1], np.zeros(4, dtype=np.uint8))
    np.testing.assert_array_equal(batch["corrected_words"][2], words[2])
    np.testing.assert_array_equal(
        batch["statuses"],
        np.array(["corrected", "corrected", "failure"], dtype=object),
    )
