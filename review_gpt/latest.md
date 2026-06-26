# Latest Review Summary

Current round: Experiment Round 08 final artifact consolidation + paper-style
figure/table export + claim audit.

## Goal

Consolidate existing paper/full/focused-scaling and long-stream benchmark
results into paper-facing artifacts for review:

- final artifact index,
- final claim audit,
- representative result table,
- component exactness table,
- final paper-style figures,
- provenance metadata.

This round does not rerun a broad full sweep, does not add
`BCH(511,484,r27)`, does not run BER, and does not implement a full OFEC or
BCH algebraic decoder.

## Skills Used

- `results-analysis`: audited CSVs, row counts, safe claim boundaries, and
  correctness support.
- `paper-figures-advise`: shaped the final figure shortlist and claim-to-figure
  mapping.
- `plot-from-data`: used for publication-style matplotlib choices.
- `research-experiment-driver`: kept final artifacts aligned with the target
  experiment story without expanding scope.
- `superpowers:test-driven-development`: added focused export tests before
  relying on the final exporter.
- `superpowers:verification-before-completion`: used for final validation.

Subagents were used in read-only mode:

- Result/claim audit subagent: inspected CSV/summary evidence and claim
  boundaries.
- Figure-design subagent: inspected existing figures/export scripts and
  recommended final figure replacements.

## Modified / Generated Files

- `scripts/export_final_paper_figures.py`
- `tests/test_final_paper_export.py`
- `results/summary/final_claim_audit.csv`
- `results/summary/final_exactness_table.csv`
- `results/summary/final_representative_table.csv`
- `results/raw/artifact_provenance.json`
- `results/paper_figures_final/fig_cache_memory_tradeoff.{png,pdf}`
- `results/paper_figures_final/fig_cache_aware_planner_oracle.{png,pdf}`
- `results/paper_figures_final/fig_candidate_testing.{png,pdf}`
- `results/paper_figures_final/fig_event_update_comparison.{png,pdf}`
- `results/paper_figures_final/fig_component_kernel_scaling.{png,pdf}`
- `results/paper_figures_final/figure_manifest.md`
- `review_gpt/final_experiment_artifact_index.md`
- `review_gpt/experiment_round_08_summary.md`
- `review_gpt/round_23_summary.md`
- `review_gpt/latest.md`

## Artifact Summary

| Artifact | Rows / files | Status |
|---|---:|---|
| `final_exactness_table.csv` | 24 rows | generated |
| `final_claim_audit.csv` | 11 rows | generated |
| `final_representative_table.csv` | 8 rows | generated |
| `results/paper_figures_final/*.png` | 5 files | generated |
| `results/paper_figures_final/*.pdf` | 5 files | generated |
| `figure_manifest.md` | 1 file | generated |
| `artifact_provenance.json` | 1 file | generated |

Exactness highlight:

- `all_double_bit_errors`
- `num_words=32385`
- `double_error_coverage=full`
- `exact_mismatch_count=0`
- `correctness_all_true=True`

Planner highlight:

- Paper preset mean planner/oracle ratio over the five workload summaries is
  about `1.041`.
- Workload-level means range from `1.000` to `1.121`.
- The figure emphasizes latency ratio rather than exact block-width match.

Candidate/event highlights:

- PackedBlockLUT is fastest in 26 of 32 representative full-preset
  candidate-test groups.
- EventUpdate flip-count 1 has about `21.45x` relative-to-from-scratch packed
  speedup in the focused summary; the benefit shrinks as flip count increases.

Long-stream cache-width semantics:

- Final artifacts use `stream_input_bits` and true `stream_input_bytes`.
- L2 evidence remains mixed and is not written as a stable strong claim.
- L3 is kept as condition-specific eBCH-like long-stream evidence.

## Recommended Final Figures

Main or near-main:

- `fig_cache_memory_tradeoff`
- `fig_cache_aware_planner_oracle`
- `fig_component_kernel_scaling`
- `fig_event_update_comparison`

Supporting:

- `fig_candidate_testing`

Internal / appendix only:

- old raw diagnostic block-width/density/batch figures,
- old planner latency figure,
- old trace-level optical workload diagnostic unless clearly labeled as
  trace-level kernel evidence.

## Commands Run

```bash
python -m pytest tests/test_final_paper_export.py -q
python scripts/summarize_results.py
python scripts/export_final_paper_figures.py
python -m pytest -q
```

Results:

- Focused export test: `1 passed, 1 warning`
- `scripts/summarize_results.py`: completed and rewrote summary CSVs
- `scripts/export_final_paper_figures.py`: completed and wrote final tables,
  figures, manifest, and provenance JSON
- Full test suite: `296 passed, 1 skipped, 27 warnings`

## Known Boundaries

- No full decoder, BER, or OFEC end-to-end claim is supported here.
- Candidate testing and component-loop results are kernel-level evidence.
- Optical trace workload results are trace-level kernel-call evidence.
- `artifact_provenance.json` records the current commit and dirty generated
  artifact state without local absolute paths.
- Unrelated untracked notes remain uncommitted:
  `review_gpt/round08_experiment_closeout_discussion.md` and
  `review_gpt/round_18_skill_and_figure_redesign_plan.md`.
