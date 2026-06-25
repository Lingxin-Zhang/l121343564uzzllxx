# Experiment Round 07 Summary

## Scope

This round completed CacheAwarePlanner calibration plus CPU paper-level
validation. It focused on the planner/rule/benchmark pipeline only.

Not included:

- no BER simulation;
- no full OFEC decoder;
- no full BCH algebraic decoder;
- no external code import;
- no paper conclusion or speedup claim;
- no `full` preset run.

## Skills and Agent Workflow

- Used `research-experiment-driver` to keep the benchmark changes tied to
  measurable planner evidence.
- Used `results-analysis` to inspect workload-level planner/oracle ratios and
  oracle match rates.
- Used `paper-figures-advise` for the Round 7 diagnostic figure organization.
- Used `superpowers:test-driven-development` for red/green tests around planner
  calibration, cache-fit fields, summary metrics, and trace semantics.
- Used `superpowers:verification-before-completion` before reporting test and
  benchmark status.
- Used two read-only explorer subagents:
  - one checked planner and benchmark schema risks;
  - one checked optical trace, summary, and plotting risks.

## Code Changes

- Calibrated `CacheAwarePlanner`:
  - dense/component batch workloads choose non-LUT paths for `batch_size < 16`;
  - dense/component batch workloads choose `PackedBlockLUTKernel` when LUTs fit
    L2/L3, including unpacked output mode;
  - packed candidate testing can choose LUT at `candidate_count >= 16`;
  - block width selection is workload-aware and avoids blindly choosing the
    largest fitting table.
- Added selection fields:
  - `uses_lut`;
  - `cache_fit_applicable`.
- Clarified optical trace semantics:
  - added `trace_uncapped_syndrome_calls`;
  - added `trace_uncapped_event_updates`;
  - retained old `executed_*` trace properties as deprecated compatibility
    aliases;
  - benchmark executed counts continue to come from prepared tasks.
- Added preset support in `bench_cache_aware_selection.py`:
  - `lightweight`;
  - `paper`;
  - `paper-small`;
  - `full`.
- Added hardware metadata output:
  - `results/raw/hardware_profile.json`.
- Added workload-level summary:
  - `results/summary/cache_aware_selection_workload_summary.csv`.
- Added Round 7 diagnostic figure:
  - `scripts/plot_experiment_round07_results.py`;
  - `results/figures/experiment_round07_cache_aware_calibration.png`;
  - `results/figures/experiment_round07_cache_aware_calibration.pdf`.

## Tests

Commands run:

```bash
python -m pytest tests/test_cache_aware_planner.py tests/test_cache_aware_selection_benchmark.py tests/test_result_summary.py tests/test_optical_workload_trace.py -q
python -m pytest -q
```

Results:

- targeted tests: `27 passed, 8 warnings`;
- full pytest: `287 passed, 1 skipped, 23 warnings`.

## Benchmarks and Outputs

Commands run:

```bash
python -m benchmarks.bench_cache_aware_selection --preset lightweight
python -m benchmarks.bench_cache_aware_selection --preset paper --append
python scripts/summarize_results.py
python scripts/plot_experiment_round07_results.py
```

Output files:

- `results/raw/cache_aware_selection.csv`
- `results/raw/hardware_profile.json`
- `results/summary/cache_aware_selection_summary.csv`
- `results/summary/cache_aware_selection_workload_summary.csv`
- `results/figures/experiment_round07_cache_aware_calibration.png`
- `results/figures/experiment_round07_cache_aware_calibration.pdf`
- `results/logs/round07_cache_aware_selection_paper.log`

CSV size:

- total rows: `450`;
- lightweight rows: `153`;
- paper rows: `297`;
- all `correctness_passed=True`.

## Experiment Results vs Paper Expectation

| Expected evidence | Artifact | Actual result | Status | Notes |
|---|---|---|---|---|
| Correctness remains exact | `results/raw/cache_aware_selection.csv` | `450/450` rows true | Meets | All selected/oracle candidates match Naive or component reference outputs. |
| Sparse single stays near oracle | workload summary | paper mean/p90/max all `1.000` | Meets | Planner selected `SparseXorKernel`. |
| Event update stays near oracle | workload summary | paper mean `1.002`, p90 `1.000`, max `1.120` | Meets | Small deviation is timing noise in one row. |
| Candidate packed stays near target | workload summary | paper mean `1.020`, p90 `1.053`, max `1.407` | Meets | Candidate threshold was lowered to `16`. |
| Dense batch improves over Round 6 | workload summary | paper mean `1.078`, p90 `1.212`, max `2.227` | Meets | Round 6 was mean `10.637`, max `26.164`. |
| Component decode batch improves over Round 6 | workload summary | paper mean `1.057`, p90 `1.163`, max `1.924` | Meets | Round 6 was mean `3.773`, max `9.163`. |
| Overall max is much lower than Round 6 | workload summary | paper max `2.227` | Meets | Round 6 max was `26.164`. |
| Cache-fit semantics are explicit | raw CSV and summary | `uses_lut` and `cache_fit_applicable` are present | Meets | Non-LUT backends no longer imply cache fit. |

## Known Issues and Next Steps

- Exact backend+block oracle match rate remains lower than backend-only match
  rate because block-width timing is workload-dependent.
- The planner is still a deterministic rule baseline, not an autotuner.
- `hardware_profile.json` has `git_dirty=True` because the benchmark was run
  before the final commit.
- Next useful step: decide whether to add `bch_511_484_r27_candidate` as a
  verified candidate profile, or keep the next round focused on paper figure
  consolidation.
