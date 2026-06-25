"""Tests for BCH reference triangulation helpers."""

from __future__ import annotations

import csv
import subprocess
import sys

import numpy as np

from tools.verify_bch_references import (
    ReferenceMatrix,
    compare_candidate,
    compare_reference_pair,
    generate_unavailable_rows,
    reference_registry_rows,
)


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


def test_reference_registry_contains_expected_sources() -> None:
    rows = reference_registry_rows()
    names = {row.reference_name for row in rows}

    assert "linux-kernel-bch" in names
    assert "python-bchlib" in names
    assert "galois" in names
    assert "ofec-cnn-local" in names
    assert "ofec-huawei" in names


def test_pairwise_comparison_identical_matrices_is_exact_match() -> None:
    matrix = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.uint8)
    left = ReferenceMatrix(
        name="left",
        reference_type="synthetic",
        parameters="n=3,r=2",
        matrix=matrix,
        notes="unit",
    )
    right = ReferenceMatrix(
        name="right",
        reference_type="synthetic",
        parameters="n=3,r=2",
        matrix=matrix.copy(),
        notes="unit",
    )

    rows = compare_reference_pair(left, right)

    identity = next(row for row in rows if row.candidate_transform == "identity")
    assert identity.exact_match is True
    assert identity.match_rate == 1.0


def test_cli_writes_registry_and_pairwise_reports(tmp_path) -> None:
    check_output = tmp_path / "bch_reference_check.csv"
    registry_output = tmp_path / "reference_registry.csv"
    pairwise_output = tmp_path / "bch_reference_pairwise_check.csv"

    result = subprocess.run(
        [
            sys.executable,
            "tools/verify_bch_references.py",
            "--output",
            str(check_output),
            "--registry-output",
            str(registry_output),
            "--pairwise-output",
            str(pairwise_output),
            "--reference",
            "none",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert check_output.exists()
    assert registry_output.exists()
    assert pairwise_output.exists()

    registry_rows = list(csv.DictReader(registry_output.open(encoding="utf-8")))
    pairwise_rows = list(csv.DictReader(pairwise_output.open(encoding="utf-8")))
    assert registry_rows
    assert pairwise_rows
