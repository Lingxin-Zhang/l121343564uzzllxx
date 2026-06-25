# Latest Review Summary

Current round: supplemental overnight experiment after Round 7.

## Goal

Run paper-targeted heavier validation because Round 7 finished early. This
round only refreshes experiment artifacts, summaries, figures, and review notes.
It does not implement new algorithms and does not add BER, a full OFEC decoder,
a full BCH algebraic decoder, or paper conclusions.

## Skills Used

- `research-experiment-driver`: used to keep the overnight run focused on
  paper-targeted validation rather than a broad full sweep.
- `results-analysis`: used to audit CSV row counts, correctness flags, exact
  mismatch counts, and planner summary metrics.
- `paper-figures-advise`: used to keep regenerated figures tied to paper-facing
  chart needs.
- `superpowers:verification-before-completion`: used before reporting test,
  benchmark, summary, figure, commit, and push status.

## Commands Run

Preflight:

```bash
python -m pytest -q
git status --short
```

Log: `results/logs/overnight_preflight.log`

Clean Round 7 planner rerun:

```bash
python -m benchmarks.bench_cache_aware_selection --preset lightweight
python -m benchmarks.bench_cache_aware_selection --preset paper --append
```

Log: `results/logs/overnight_cache_aware_selection.log`

Core paper-targeted benchmarks:

```bash
python -m benchmarks.bench_cache_aware --preset full --repeats 7
python -m benchmarks.bench_component_decoder_exactness --preset full --repeats 7
python -m benchmarks.bench_candidate_testing --preset full --repeats 7
```

Logs:

- `results/logs/overnight_cache_aware_full.log`
- `results/logs/overnight_component_decoder_exactness_full.log`
- `results/logs/overnight_candidate_testing_full.log`

Component-kernel scaling supplements:

```bash
python -m benchmarks.bench_bch_syndrome --matrix-source galois_systematic_candidate --total-bits 1000000,10000000,50000000 --iterations 1,5,10 --repeats 5
python -m benchmarks.bench_component_loop --matrix-source galois_systematic_candidate --num-words 4096,16384,65536,262144 --iterations 1,5,10 --repeats 5
python -m benchmarks.bench_event_update --matrix-source galois_systematic_candidate --flip-counts 1,2,4,8,16 --iterations 1,5,10 --repeats 5
```

Logs:

- `results/logs/overnight_bch_syndrome.log`
- `results/logs/overnight_component_loop.log`
- `results/logs/overnight_event_update.log`

Summary and figure regeneration:

```bash
python scripts/summarize_results.py
python scripts/plot_results.py
python scripts/plot_experiment_round07_results.py
python scripts/export_paper_figures.py
```

Log: `results/logs/overnight_summary_and_figures.log`

Acceptance:

```bash
python -m pytest -q
```

Plus CSV/figure audit. Log: `results/logs/overnight_acceptance.log`

## Outputs Refreshed

- `results/raw/cache_aware_selection.csv`
- `results/raw/cache_aware.csv`
- `results/raw/candidate_testing.csv`
- `results/raw/component_decoder_exactness.csv`
- `results/raw/bch_syndrome.csv`
- `results/raw/component_loop.csv`
- `results/raw/event_update.csv`
- `results/raw/hardware_profile.json`
- `results/summary/*.csv`
- `results/figures/*.png`
- `results/figures/*.pdf`
- `results/paper_figures/*.png`
- `results/paper_figures/*.pdf`
- `results/logs/overnight_*.log`

## Artifact Audit

| Artifact | Rows | Bad correctness | Notes |
|---|---:|---:|---|
| `cache_aware_selection.csv` | 450 | 0 | lightweight + paper presets |
| `cache_aware.csv` | 9216 | 0 | full preset, repeats 7 |
| `candidate_testing.csv` | 784 | 0 | full preset, repeats 7 |
| `component_decoder_exactness.csv` | 24 | 0 | full preset, repeats 7 |
| `bch_syndrome.csv` | 36 | 0 | focused scaling, repeats 5 |
| `component_loop.csv` | 48 | 0 | focused scaling, repeats 5 |
| `event_update.csv` | 45 | 0 | flip counts through 16, repeats 5 |

`component_decoder_exactness.csv` has `exact_mismatch_count=0` for all rows.
The full double-bit case is labeled `all_double_bit_errors` with
`double_error_coverage=full`.

## Planner Summary After Overnight Rerun

Paper preset workload metrics from
`results/summary/cache_aware_selection_workload_summary.csv`:

| Workload | Mean planner/oracle | p90 | Max | Correctness |
|---|---:|---:|---:|---|
| `candidate_test_packed` | 1.018 | 1.062 | 1.268 | True |
| `component_decode_batch` | 1.063 | 1.169 | 2.246 | True |
| `dense_batch` | 1.121 | 1.363 | 2.517 | True |
| `event_update` | 1.001 | 1.000 | 1.090 | True |
| `sparse_single` | 1.000 | 1.000 | 1.000 | True |

These results remain near the Round 7 calibrated quality. They are suitable as
paper-level validation data for planner behavior, with the caveat that exact
backend+block oracle match remains timing-sensitive.

## Figure Status

Regenerated:

- `results/figures/experiment_round07_cache_aware_calibration.png`
- `results/figures/experiment_round07_cache_aware_calibration.pdf`
- `results/figures/bch_syndrome_throughput.png`
- `results/figures/component_loop_speedup.png`
- `results/figures/event_update_comparison.png`
- `results/paper_figures/fig_bch_syndrome_throughput.png`
- `results/paper_figures/fig_component_loop_latency.png`
- `results/paper_figures/fig_event_update_comparison.png`
- `results/paper_figures/fig_planner_latency.png`

The `results/paper_figures/` outputs are better suited for paper drafting than
the older diagnostic figures, but captions and final figure selection should
still be reviewed before manuscript use.

## Skipped Items

- `scripts/run_all_benchmarks.py` was intentionally not run because it is broad
  and less targeted than the selected paper-facing experiments.
- No extra full sweep beyond the specified targeted commands.
- No `BCH(511,484,r27)` candidate profile was added.
- No BER/full-decoder experiments were run.

## Known Notes

- `results/raw/hardware_profile.json` may still record `git_dirty=True`
  because result/log files were generated during the run. The code was the
  committed Round 7 code at experiment start.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains untracked and
  was not staged.
- `paper/`, `references/`, and `external_refs/` were not committed.
