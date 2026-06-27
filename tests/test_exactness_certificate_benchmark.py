"""Smoke tests for the exactness certificate benchmark."""

from __future__ import annotations

import numpy as np

from benchmarks.bench_exactness_certificate import (
    MatrixSpec,
    run_exactness_certificate_rows,
)


def test_exactness_certificate_rows_report_zero_mismatches_for_small_matrix() -> None:
    matrix = np.eye(4, dtype=np.uint8)

    rows = run_exactness_certificate_rows(
        matrix_specs=(MatrixSpec("toy_4_3", matrix, k=2),),
        random_batch_size=8,
        decoder_random_words=8,
        block_width=2,
    )

    assert rows
    assert {row["profile"] for row in rows} == {"toy_4_3"}
    assert all(row["mismatch_count"] == 0 for row in rows)
    assert any(row["check_name"] == "parity_single_bit" for row in rows)
    assert any(row["check_name"] == "syndrome_double_bit" for row in rows)
    assert any(row["check_name"] == "bdd_decoder_consistency" for row in rows)
