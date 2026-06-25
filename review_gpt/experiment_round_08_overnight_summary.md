# Experiment Round 08 Overnight Summary

## Scope

This is a supplemental overnight experiment round because Round 7 completed
early. The goal was paper-targeted heavier validation, not a broad full sweep.

No new backend, BER simulation, full OFEC decoder, full BCH algebraic decoder,
or paper conclusion was added.

## Commands and Logs

| Step | Command summary | Log |
|---|---|---|
| Preflight | `python -m pytest -q`; `git status --short` | `results/logs/overnight_preflight.log` |
| Planner rerun | `bench_cache_aware_selection` lightweight + paper append | `results/logs/overnight_cache_aware_selection.log` |
| Cache-aware full | `bench_cache_aware --preset full --repeats 7` | `results/logs/overnight_cache_aware_full.log` |
| Component exactness full | `bench_component_decoder_exactness --preset full --repeats 7` | `results/logs/overnight_component_decoder_exactness_full.log` |
| Candidate testing full | `bench_candidate_testing --preset full --repeats 7` | `results/logs/overnight_candidate_testing_full.log` |
| BCH syndrome scaling | `bench_bch_syndrome` with total bits through `50000000` | `results/logs/overnight_bch_syndrome.log` |
| Component loop scaling | `bench_component_loop` with num words through `262144` | `results/logs/overnight_component_loop.log` |
| Event update scaling | `bench_event_update` with flip counts through `16` | `results/logs/overnight_event_update.log` |
| Summary and figures | `summarize_results`, `plot_results`, Round 7 plot, paper figure export | `results/logs/overnight_summary_and_figures.log` |
| Acceptance | final `pytest` and CSV/figure audit | `results/logs/overnight_acceptance.log` |

All planned targeted commands completed. No long command was skipped for time.
`scripts/run_all_benchmarks.py` was intentionally not run.

## Artifact Summary

| Artifact | Rows | Bad correctness | Notes |
|---|---:|---:|---|
| `results/raw/cache_aware_selection.csv` | 450 | 0 | lightweight + paper planner validation |
| `results/raw/cache_aware.csv` | 9216 | 0 | full cache-aware block-width/density/batch grid |
| `results/raw/candidate_testing.csv` | 784 | 0 | full candidate-pattern benchmark |
| `results/raw/component_decoder_exactness.csv` | 24 | 0 | full component exactness |
| `results/raw/bch_syndrome.csv` | 36 | 0 | focused BCH syndrome scaling |
| `results/raw/component_loop.csv` | 48 | 0 | focused component-loop scaling |
| `results/raw/event_update.csv` | 45 | 0 | event update flip-count scaling |

`component_decoder_exactness.csv` has `exact_mismatch_count=0` for every row.
The full double-bit case is present as `all_double_bit_errors` with
`double_error_coverage=full`.

## Planner Validation Snapshot

From `results/summary/cache_aware_selection_workload_summary.csv`, paper
preset:

| Workload | Mean planner/oracle | p90 | Max | Correctness |
|---|---:|---:|---:|---|
| `candidate_test_packed` | 1.018 | 1.062 | 1.268 | True |
| `component_decode_batch` | 1.063 | 1.169 | 2.246 | True |
| `dense_batch` | 1.121 | 1.363 | 2.517 | True |
| `event_update` | 1.001 | 1.000 | 1.090 | True |
| `sparse_single` | 1.000 | 1.000 | 1.000 | True |

The overnight rerun preserves the Round 7 calibration quality. It is suitable
as paper-level planner validation data, while exact backend+block oracle match
should still be described as timing-sensitive.

## Figure Outputs

Regenerated diagnostic figures under `results/figures/` and paper-style exports
under `results/paper_figures/`.

Important files for review:

- `results/figures/experiment_round07_cache_aware_calibration.png`
- `results/figures/bch_syndrome_throughput.png`
- `results/figures/component_loop_speedup.png`
- `results/figures/event_update_comparison.png`
- `results/paper_figures/fig_bch_syndrome_throughput.png`
- `results/paper_figures/fig_component_loop_latency.png`
- `results/paper_figures/fig_event_update_comparison.png`
- `results/paper_figures/fig_planner_latency.png`

The paper-style figures are now backed by heavier CSVs, but final paper figure
selection and caption wording still need a separate review.

## Verification

Final acceptance:

- `python -m pytest -q`: `287 passed, 1 skipped, 23 warnings`.
- CSV/figure audit: passed.
- All checked raw CSVs have `bad_correctness=0`.
- Component exactness has `bad_exact_mismatch=0`.

## Clean-Room / Public Repo Notes

- No external code was copied.
- No BER/full-decoder claims were made.
- `paper/`, `references/`, `external_refs/`, and `AGENTS.local.md` were not
  staged.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains untracked and
  was intentionally not staged.
