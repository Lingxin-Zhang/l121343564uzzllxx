"""Tests for benchmark-semantics documentation."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_known_hit_collision_semantics_are_documented() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs = (ROOT / "docs" / "benchmark_semantics.md").read_text(encoding="utf-8")
    combined = f"{readme}\n{docs}"

    assert "known-hit mode" in combined
    assert "matches_found is guaranteed to be at least one" in combined
    assert "different candidate masks can share the same syndrome" in combined


def test_huawei_reference_boundary_is_documented() -> None:
    notes = (ROOT / "docs" / "reference_inspection_notes.md").read_text(encoding="utf-8")

    assert "HUAWEI-OFEC-Tao is treated as reference-only engineering context" in notes
    assert "not claimed to reproduce its mini-TPC/OFEC decoder schedule" in notes
