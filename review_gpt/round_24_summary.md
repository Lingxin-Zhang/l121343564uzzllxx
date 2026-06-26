# Round 24 Summary

This round corresponds to Experiment Round 08.1: cache-aware artifact fix and
final export data-quality guard.

## Modified / Generated Files

- `scripts/export_final_paper_figures.py`
- `tests/test_final_paper_export.py`
- `tests/test_result_summary.py`
- `results/summary/final_representative_table.csv`
- `results/raw/artifact_provenance.json`
- `results/paper_figures_final/*.pdf`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_08_summary.md`
- `review_gpt/experiment_round_08_1_cache_aware_artifact_fix.md`

## Key Fixes

- Confirmed `cache_aware.csv` and `cache_aware_summary.csv` are non-empty and
  contain required BCH/eBCH PackedBlockLUT block-width rows.
- Added final export guards so empty critical data sources raise explicit
  errors instead of producing empty figures.
- Updated Candidate testing representative selection to prefer BCH/eBCH
  profiles before synthetic fallback.

## Scope Boundaries

- No new benchmark sweep.
- No `BCH(511,484,r27)`.
- No BER or full decoder work.
- No stronger L2/L3 claim.
