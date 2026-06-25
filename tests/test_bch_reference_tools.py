"""Tests for BCH reference triangulation helpers."""

from __future__ import annotations

import csv
import subprocess
import sys

import numpy as np

from tools.verify_bch_references import (
    ReferenceMatrix,
    build_reference_summary,
    inspect_ofec_dependency,
    matrix_candidate_rows,
    compare_candidate,
    compare_reference_pair,
    generate_pairwise_rows,
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
    registry_output = tmp_path / "reference_registry.csv"
    pairwise_output = tmp_path / "bch_reference_pairwise_check.csv"
    summary_output = tmp_path / "bch_reference_summary.csv"
    candidate_output = tmp_path / "bch_matrix_candidate_check.csv"
    dependency_output = tmp_path / "ofec_dependency_check.csv"
    result = subprocess.run(
        [
            sys.executable,
            "tools/verify_bch_references.py",
            "--output",
            str(output),
            "--registry-output",
            str(registry_output),
            "--pairwise-output",
            str(pairwise_output),
            "--summary-output",
            str(summary_output),
            "--candidate-output",
            str(candidate_output),
            "--dependency-output",
            str(dependency_output),
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


def test_generate_pairwise_rows_requires_two_references() -> None:
    matrix = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    only = ReferenceMatrix(
        name="only",
        reference_type="synthetic",
        parameters="n=2,r=2",
        matrix=matrix,
        notes="unit",
    )

    rows = generate_pairwise_rows([only])

    assert len(rows) == 1
    assert rows[0].left_reference == "not_enough_available_references"
    assert "requires at least two" in rows[0].notes


def test_summary_row_matches_pairwise_rows() -> None:
    matrix = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    left = ReferenceMatrix(
        name="left",
        reference_type="synthetic",
        parameters="n=2,r=2",
        matrix=matrix,
        notes="unit",
    )
    right = ReferenceMatrix(
        name="right",
        reference_type="synthetic",
        parameters="n=2,r=2",
        matrix=matrix.copy(),
        notes="unit",
    )
    pairwise_rows = generate_pairwise_rows([left, right])

    summary = build_reference_summary(
        enabled_references=("left", "right", "missing"),
        available_references=[left, right],
        unavailable_references=("missing",),
        pairwise_rows=pairwise_rows,
    )

    assert summary.num_enabled_references == 3
    assert summary.available_references == "left;right"
    assert summary.unavailable_references == "missing"
    assert summary.num_pairwise_rows == len(pairwise_rows)
    assert summary.any_pairwise_exact_match is True
    assert "left|right|identity|1.000000" == summary.best_pairwise_match
    assert summary.current_matrix_status == "placeholder"


def test_matrix_candidate_rows_include_placeholder_and_candidate() -> None:
    reference_matrix = np.array([[1, 0], [0, 1]], dtype=np.uint8)
    reference = ReferenceMatrix(
        name="synthetic",
        reference_type="unit",
        parameters="n=2,r=2",
        matrix=reference_matrix,
        notes="unit",
    )
    local_matrices = {
        "placeholder": reference_matrix,
        "galois_systematic_candidate": reference_matrix.copy(),
    }

    rows = matrix_candidate_rows(
        local_matrices=local_matrices,
        available_references=[reference],
        unavailable_reference_names=(),
    )

    names = {row.local_matrix_name for row in rows}
    assert names == {"placeholder", "galois_systematic_candidate"}
    exact_rows = [
        row
        for row in rows
        if row.local_matrix_name == "galois_systematic_candidate"
        and row.candidate_transform == "identity"
    ]
    assert exact_rows
    assert exact_rows[0].exact_match is True


def test_inspect_ofec_dependency_reports_galois_usage(tmp_path) -> None:
    codec_dir = tmp_path / "ofec" / "codec"
    codec_dir.mkdir(parents=True)
    (codec_dir / "_ebch_lut.py").write_text(
        "import galois\n"
        "def build_syndrome_lut_tables():\n"
        "    bch = galois.BCH(255, 239)\n"
        "    return bch\n",
        encoding="utf-8",
    )

    rows = inspect_ofec_dependency(str(tmp_path))

    assert rows
    row = rows[0]
    assert row.inspected_file_name == "_ebch_lut.py"
    assert row.has_import_galois is True
    assert row.has_galois_bch is True
    assert "not_independent" in row.independence_status


def test_cli_writes_registry_and_pairwise_reports(tmp_path) -> None:
    check_output = tmp_path / "bch_reference_check.csv"
    registry_output = tmp_path / "reference_registry.csv"
    pairwise_output = tmp_path / "bch_reference_pairwise_check.csv"
    summary_output = tmp_path / "bch_reference_summary.csv"
    candidate_output = tmp_path / "bch_matrix_candidate_check.csv"
    dependency_output = tmp_path / "ofec_dependency_check.csv"

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
            "--summary-output",
            str(summary_output),
            "--candidate-output",
            str(candidate_output),
            "--dependency-output",
            str(dependency_output),
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
    assert summary_output.exists()
    assert candidate_output.exists()
    assert dependency_output.exists()

    registry_rows = list(csv.DictReader(registry_output.open(encoding="utf-8")))
    pairwise_rows = list(csv.DictReader(pairwise_output.open(encoding="utf-8")))
    summary_rows = list(csv.DictReader(summary_output.open(encoding="utf-8")))
    candidate_rows = list(csv.DictReader(candidate_output.open(encoding="utf-8")))
    dependency_rows = list(csv.DictReader(dependency_output.open(encoding="utf-8")))
    assert registry_rows
    assert pairwise_rows
    assert summary_rows
    assert candidate_rows
    assert dependency_rows
    assert summary_rows[0]["num_pairwise_rows"] == str(len(pairwise_rows))
