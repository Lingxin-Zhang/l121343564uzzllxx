"""Tests for BCH reference triangulation helpers."""

from __future__ import annotations

import csv
import subprocess
import sys

import numpy as np

from tools.verify_bch_references import compare_candidate, generate_unavailable_rows


def test_cli_help_runs() -> None:
    result = subprocess.run(
        [sys.executable, "tools/verify_bch_references.py", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "--output" in result.stdout


def test_compare_identical_matrices_is_exact_match() -> None:
    matrix = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.uint8)

    rows = compare_candidate(
        reference_name="synthetic",
        reference_type="unit",
        parameters="n=3,r=2",
        reference_matrix=matrix,
        ours_matrix=matrix,
    )

    identity = next(row for row in rows if row.candidate_transform == "identity")
    assert identity.exact_match is True
    assert identity.num_equal_entries == 6
    assert identity.num_total_entries == 6
    assert identity.match_rate == 1.0


def test_compare_reversed_positions_detects_transform() -> None:
    ours = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.uint8)
    reference = ours[::-1]

    rows = compare_candidate(
        reference_name="synthetic",
        reference_type="unit",
        parameters="n=3,r=2",
        reference_matrix=reference,
        ours_matrix=ours,
    )

    reverse_positions = next(
        row for row in rows if row.candidate_transform == "reverse_codeword_positions"
    )
    assert reverse_positions.exact_match is True
    assert reverse_positions.match_rate == 1.0


def test_unavailable_rows_and_cli_report_are_graceful(tmp_path) -> None:
    unavailable = generate_unavailable_rows(
        enabled_references=("ofec", "python-bchlib"),
        reason_by_reference={"ofec": "not configured"},
    )

    assert [row.reference_name for row in unavailable] == ["ofec", "python-bchlib"]
    assert unavailable[0].reference_available is False

    output = tmp_path / "bch_reference_check.csv"
    result = subprocess.run(
        [
            sys.executable,
            "tools/verify_bch_references.py",
            "--output",
            str(output),
            "--reference",
            "none",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert rows
    assert rows[0]["reference_available"] == "False"
