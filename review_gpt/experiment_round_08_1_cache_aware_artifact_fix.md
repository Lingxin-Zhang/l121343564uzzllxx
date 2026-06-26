# Experiment Round 08.1 Summary

Round 8.1 restores the cache-aware evidence chain and adds final-export
data-quality guards. This is not a new experiment round and not a paper-writing
round.

## Problem

Review flagged that these files could be empty while still being used as
primary evidence for the cache/memory/block-width trade-off:

- `results/raw/cache_aware.csv`
- `results/summary/cache_aware_summary.csv`

That would make `fig_cache_memory_tradeoff`, `final_representative_table.csv`,
the figure manifest, and the claim audit appear valid even if the key
cache-aware data was missing.

## Artifact Audit

Current checked-out artifacts are non-empty, so no targeted rerun was needed.

| Artifact | Rows | Notes |
|---|---:|---|
| `results/raw/cache_aware.csv` | 9216 | includes BCH/eBCH and PackedBlockLUT rows |
| `results/summary/cache_aware_summary.csv` | 9216 | includes BCH/eBCH and PackedBlockLUT rows |

Coverage for the final cache-memory figure:

- profiles: `bch_255_239_r16`, `ebch_256_239_r17`
- backend: `PackedBlockLUT.apply_many_packed`
- batch size: `4096`
- density: `0.05`
- block widths: `4,6,8,10,12,14,16,18,20`
- correctness: all true

Restoration source:

- Current repository artifacts already contain the non-empty cache-aware CSVs.
- No benchmark rerun was performed in this round.

## Code Fixes

- `scripts/export_final_paper_figures.py`
  - Added `require_rows()` guard for critical data sources.
  - Added validation for non-empty `cache_aware.csv`.
  - Added validation for non-empty `cache_aware_summary.csv`.
  - Added validation that `fig_cache_memory_tradeoff` has actual cache-aware
    PackedBlockLUT rows.
  - Added validation for long-stream, planner, candidate, event-update, BCH
    syndrome, component-loop, and exactness inputs.
  - Changed `final_representative_table.csv` candidate-row selection to prefer
    `bch_255_239_r16`, then `ebch_256_239_r17`, then fallback profiles.

- `tests/test_final_paper_export.py`
  - Added a test that export fails when `cache_aware_summary.csv` is empty.
  - Added a test that the Candidate testing representative row uses BCH/eBCH
    before synthetic profiles.
  - Added a test that the Cache/memory trade-off row points to a non-empty
    source CSV.
  - Added a provenance check that generated metadata does not contain local
    absolute paths.

- `tests/test_result_summary.py`
  - Added a unit test for cache-aware summary fields, block width, LUT bytes,
    cache-fit fields, and correctness aggregation.

## Regenerated Artifacts

Regenerated after the fix:

- `results/summary/final_claim_audit.csv`
- `results/summary/final_exactness_table.csv`
- `results/summary/final_representative_table.csv`
- `results/paper_figures_final/*.pdf`
- `results/raw/artifact_provenance.json`

The final Candidate testing row now uses `bch_255_239_r16`.

## Commands Run

```bash
python -m pytest tests/test_final_paper_export.py tests/test_result_summary.py -q
python scripts/summarize_results.py
python scripts/export_final_paper_figures.py
python -m pytest -q
```

Results:

- Targeted tests: `12 passed, 1 warning`
- Summarizer: completed
- Final exporter: completed
- Full pytest: `298 passed, 1 skipped, 27 warnings`

## Boundaries

- No new `BCH(511,484,r27)`.
- No BER.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No broad full sweep.
- No paper-text rewrite.
- No stronger L2/L3 claim.
- No `paper/`, `references/`, `external_refs/`, `AGENTS.local.md`, or local
  absolute paths should be committed.
