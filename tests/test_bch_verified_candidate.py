"""Tests for the verified-candidate BCH matrix construction."""

from __future__ import annotations

import os

import numpy as np
import pytest

from codes.bch_like import make_bch255_t2_syndrome_matrix_galois_systematic
from tools.verify_bch_references import probe_galois_reference, probe_ofec_reference

pytest.importorskip("galois")


def test_galois_systematic_candidate_shape_dtype_and_bits() -> None:
    matrix = make_bch255_t2_syndrome_matrix_galois_systematic()

    assert matrix.shape == (255, 16)
    assert matrix.dtype == np.uint8
    assert set(np.unique(matrix)).issubset({0, 1})


def test_galois_systematic_candidate_is_deterministic() -> None:
    first = make_bch255_t2_syndrome_matrix_galois_systematic()
    second = make_bch255_t2_syndrome_matrix_galois_systematic()

    np.testing.assert_array_equal(first, second)


def test_galois_systematic_candidate_zero_syndrome_for_encoded_words() -> None:
    matrix = make_bch255_t2_syndrome_matrix_galois_systematic()
    rng = np.random.default_rng(20260625)

    for _ in range(8):
        message = rng.integers(0, 2, size=239, dtype=np.uint8)
        parity = (message @ matrix[:239, :]) & 1
        codeword = np.concatenate([message, parity]).astype(np.uint8, copy=False)
        syndrome = (codeword @ matrix) & 1

        np.testing.assert_array_equal(syndrome, np.zeros(16, dtype=np.uint8))


def test_galois_systematic_candidate_matches_galois_reference_probe() -> None:
    candidate = make_bch255_t2_syndrome_matrix_galois_systematic()
    reference = probe_galois_reference()

    np.testing.assert_array_equal(candidate, reference.matrix)


def test_galois_systematic_candidate_matches_optional_ofec_reference() -> None:
    ofec_path = os.environ.get("BCH_REF_OFEC_PATH")
    if not ofec_path:
        pytest.skip("BCH_REF_OFEC_PATH is not configured")

    candidate = make_bch255_t2_syndrome_matrix_galois_systematic()
    reference = probe_ofec_reference(ofec_path)

    np.testing.assert_array_equal(candidate, reference.matrix)
