from __future__ import annotations

import csv
import json
from pathlib import Path

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
