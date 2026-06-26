from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from scripts.export_final_paper_figures import main as export_final_main


def test_export_final_paper_figures_writes_tables_figures_and_manifest(tmp_path: Path) -> None:
    figure_dir = tmp_path / "paper_figures_final"
    summary_dir = tmp_path / "summary"
    raw_dir = tmp_path / "raw"

    exit_code = export_final_main(
        [
            "--raw-dir",
            "results/raw",
            "--summary-dir",
            "results/summary",
            "--figure-dir",
            str(figure_dir),
            "--final-summary-dir",
            str(summary_dir),
            "--provenance-output",
            str(raw_dir / "artifact_provenance.json"),
        ]
    )

    assert exit_code == 0
    for name in (
        "final_claim_audit.csv",
        "final_representative_table.csv",
        "final_exactness_table.csv",
    ):
        path = summary_dir / name
        assert path.exists()
        with path.open(newline="", encoding="utf-8") as f:
            assert list(csv.DictReader(f))

    provenance = json.loads((raw_dir / "artifact_provenance.json").read_text())
    assert "code_commit_hash" in provenance
    assert "dirty_paths_summary" in provenance
    provenance_text = json.dumps(provenance)
    assert "D:\\" not in provenance_text
    assert "C:\\" not in provenance_text

    for stem in (
        "fig_cache_memory_tradeoff",
        "fig_cache_aware_planner_oracle",
        "fig_candidate_testing",
        "fig_event_update_comparison",
        "fig_component_kernel_scaling",
    ):
        assert (figure_dir / f"{stem}.png").exists()
        assert (figure_dir / f"{stem}.pdf").exists()

    manifest = figure_dir / "figure_manifest.md"
    assert manifest.exists()
    manifest_text = manifest.read_text(encoding="utf-8")
    assert "fig_cache_memory_tradeoff" in manifest_text
    assert "stream_input_bits" in manifest_text

    representative_rows = list(
        csv.DictReader((summary_dir / "final_representative_table.csv").open(encoding="utf-8"))
    )
    candidate_row = next(row for row in representative_rows if row["experiment"] == "Candidate testing")
    assert any(
        profile in candidate_row["profile_or_workload"]
        for profile in ("bch_255_239_r16", "ebch_256_239_r17")
    )

    cache_row = next(row for row in representative_rows if row["experiment"] == "Cache/memory trade-off")
    source_path = Path(cache_row["source_csv"])
    with source_path.open(newline="", encoding="utf-8") as f:
        assert list(csv.DictReader(f))


def test_export_final_paper_figures_rejects_empty_cache_aware_summary(tmp_path: Path) -> None:
    summary_dir = tmp_path / "summary"
    figure_dir = tmp_path / "figures"
    raw_dir = tmp_path / "raw"
    _copy_summary_csvs(Path("results/summary"), summary_dir)

    cache_summary = summary_dir / "cache_aware_summary.csv"
    header = cache_summary.read_text(encoding="utf-8").splitlines()[0]
    cache_summary.write_text(header + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cache_aware_summary.csv has no rows"):
        export_final_main(
            [
                "--raw-dir",
                "results/raw",
                "--summary-dir",
                str(summary_dir),
                "--figure-dir",
                str(figure_dir),
                "--final-summary-dir",
                str(tmp_path / "final_summary"),
                "--provenance-output",
                str(raw_dir / "artifact_provenance.json"),
            ]
        )


def _copy_summary_csvs(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.glob("*.csv"):
        shutil.copy2(path, destination / path.name)
