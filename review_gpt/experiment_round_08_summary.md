# Experiment Round 08 Summary

Round 08 is final artifact consolidation: tables, paper-style figures,
provenance metadata, and claim audit. It uses existing paper/full/focused
scaling and long-stream results; it does not rerun broad benchmarks.

## Scope

Done:

- Added `scripts/export_final_paper_figures.py`.
- Added `tests/test_final_paper_export.py`.
- Generated final summary tables:
  - `results/summary/final_exactness_table.csv`
  - `results/summary/final_claim_audit.csv`
  - `results/summary/final_representative_table.csv`
- Generated final figure outputs in `results/paper_figures_final/`.
- Generated `results/paper_figures_final/figure_manifest.md`.
- Generated `results/raw/artifact_provenance.json`.
- Added `review_gpt/final_experiment_artifact_index.md`.

Not done:

- No new `BCH(511,484,r27)` profile.
- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No broad full sweep.
- No final paper text rewrite.

## Final Tables

| Table | Rows | Notes |
|---|---:|---|
| `final_exactness_table.csv` | 24 | full-preset component exactness; all-double-bit rows have 32385 words and zero mismatches |
| `final_claim_audit.csv` | 11 | maps safe claims to supporting artifacts and cautions |
| `final_representative_table.csv` | 8 | compact representative runtime/exactness/provenance table |

## Final Figures

| Figure | Role |
|---|---|
| `fig_cache_memory_tradeoff.{png,pdf}` | main cache/memory/block-width trade-off figure |
| `fig_cache_aware_planner_oracle.{png,pdf}` | main planner vs measured oracle figure |
| `fig_candidate_testing.{png,pdf}` | candidate-heavy supporting figure |
| `fig_event_update_comparison.{png,pdf}` | low-flip update figure |
| `fig_component_kernel_scaling.{png,pdf}` | BCH syndrome and component-loop scaling figure |

## Claim Boundaries

- Component exactness is supported for the tested component model, including
  full double-error coverage with `exact_mismatch_count=0`.
- CacheAwarePlanner is supported as a near-oracle heuristic in the paper preset,
  with latency ratio emphasized over exact block-width match.
- PackedBlockLUT candidate-test and component-kernel speedups are kernel-level
  evidence, not full decoder or BER results.
- Long-stream cache-width results use the corrected `stream_input_bits` /
  `stream_input_bytes` schema.
- L2 remains mixed and should not be written as a stable strong claim.
- L3 is condition-specific evidence for the tested eBCH-like long-stream case.

## Skills and Subagents

Skills used:

- `results-analysis` for CSV and claim-boundary audit.
- `paper-figures-advise` and `plot-from-data` for final figure design.
- `research-experiment-driver` for selecting paper-facing artifacts without
  widening scope.
- `superpowers:test-driven-development` for adding a focused export test.
- `superpowers:verification-before-completion` before final completion checks.

Subagents used:

- Result/claim audit subagent: read-only artifact and claim support audit.
- Figure-design subagent: read-only paper-figure redesign audit.

## Commands

```bash
python -m pytest tests/test_final_paper_export.py -q
python scripts/summarize_results.py
python scripts/export_final_paper_figures.py
```

Final verification commands are recorded in `review_gpt/latest.md`.
