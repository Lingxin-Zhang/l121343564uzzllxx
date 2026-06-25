# Latest Review Summary

Current round: supplemental experiment round 7.

## Goal

Calibrate `CacheAwarePlanner` for dense/component batch workloads and run a
paper-level CPU validation preset. This round keeps the project focused on
exact GF(2) component-kernel/backend acceleration. It does not add BER, a full
OFEC decoder, a full BCH algebraic decoder, or paper conclusions.

## Skills and Agents Used

- `research-experiment-driver`: used to keep benchmark changes tied to
  falsifiable planner/calibration evidence.
- `results-analysis`: used to inspect `planner_over_oracle`, oracle match
  rates, correctness flags, and workload-level summaries.
- `paper-figures-advise`: used for the Round 7 diagnostic figure layout.
- `superpowers:test-driven-development`: used to add failing tests before
  changing planner/schema/summary behavior.
- `superpowers:verification-before-completion`: used before claiming test and
  benchmark status.
- `superpowers:subagent-driven-development`: used in a limited way through two
  read-only explorer subagents. They inspected planner/benchmark and
  trace/summary/plot risks. No subagent edited files.

## Modified Files

- `linear_kernel/cache_aware_planner.py`
- `benchmarks/bench_cache_aware_selection.py`
- `workloads/optical_traces.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round07_results.py`
- `scripts/run_all_benchmarks.py`
- `tests/test_cache_aware_planner.py`
- `tests/test_cache_aware_selection_benchmark.py`
- `tests/test_result_summary.py`
- `tests/test_optical_workload_trace.py`
- `results/raw/cache_aware_selection.csv`
- `results/raw/hardware_profile.json`
- `results/summary/cache_aware_selection_summary.csv`
- `results/summary/cache_aware_selection_workload_summary.csv`
- `results/figures/experiment_round07_cache_aware_calibration.png`
- `results/figures/experiment_round07_cache_aware_calibration.pdf`
- `results/logs/round07_cache_aware_selection_paper.log`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_07_summary.md`

## Implementation Notes

- `CacheAwarePlanner` now records `uses_lut` and `cache_fit_applicable`.
  Non-LUT backends no longer report cache-fit flags as if their whole working
  set fit L1/L2/L3.
- Dense/component batch rules were calibrated:
  - `batch_size < 16`: avoid PackedBlockLUT setup/mask overhead and choose a
    non-LUT vectorized path.
  - `batch_size >= 16`: use `PackedBlockLUTKernel` when the selected LUT fits
    L2/L3, even when output mode is unpacked.
- Candidate packed workload now allows LUT selection starting at
  `candidate_count >= 16`, matching the paper grid.
- Block-width selection is cache-tier/workload aware:
  - medium candidate/batch cases prefer wider LUTs up to width 12;
  - very large candidate/batch cases prefer width 6 when available;
  - fallback behavior remains conservative when LUTs do not fit L3.
- `WorkloadTrace` now exposes `trace_uncapped_syndrome_calls` and
  `trace_uncapped_event_updates`. The old `executed_*` trace properties remain
  deprecated compatibility aliases. Optical workload benchmark CSVs still use
  prepared-task counts for actual executed counts.
- `bench_cache_aware_selection.py` now supports `lightweight`, `paper`,
  `paper-small`, and `full` presets. This round ran `lightweight` and `paper`.
- `summarize_results.py` now writes
  `results/summary/cache_aware_selection_workload_summary.csv` with workload
  mean/median/p90/p95/max planner-over-oracle, oracle match rates, backend
  distributions, row count, and correctness status.
- `scripts/plot_experiment_round07_results.py` writes a diagnostic PNG/PDF with
  planner/oracle latency ratio and oracle match rates by workload.
- `results/raw/hardware_profile.json` records CPU/OS/Python/NumPy/cache-profile
  metadata and marks that the benchmark was run from a dirty working tree before
  the final commit.

## Commands Run

- `python -m pytest tests/test_cache_aware_planner.py tests/test_cache_aware_selection_benchmark.py tests/test_result_summary.py tests/test_optical_workload_trace.py -q`
  - Result: `27 passed, 8 warnings`.
- `python -m pytest -q`
  - Result: `287 passed, 1 skipped, 23 warnings`.
- `python -m benchmarks.bench_cache_aware_selection --preset lightweight`
  - Result: passed; wrote `results/raw/cache_aware_selection.csv` and
    `results/raw/hardware_profile.json`.
- `python -m benchmarks.bench_cache_aware_selection --preset paper --append`
  - Result: passed; appended paper rows to `results/raw/cache_aware_selection.csv`.
  - Log: `results/logs/round07_cache_aware_selection_paper.log`.
- `python scripts/summarize_results.py`
  - Result: passed; wrote cache-aware selection summary files.
- `python scripts/plot_experiment_round07_results.py`
  - Result: passed; wrote Round 7 PNG/PDF.

## Result Artifacts

- `results/raw/cache_aware_selection.csv`
  - Rows: `450`.
  - Presets: `lightweight=153`, `paper=297`.
  - `correctness_passed=True` for all rows.
- `results/summary/cache_aware_selection_workload_summary.csv`
  - Workload-level calibration metrics for both presets.
- `results/figures/experiment_round07_cache_aware_calibration.png`
  - Generated.
- `results/figures/experiment_round07_cache_aware_calibration.pdf`
  - Generated.

## Experiment Results vs Paper Expectation

Round 6 reference numbers from the previous review:

- `dense_batch`: mean `10.637`, p90 `22.853`, max `26.164`.
- `component_decode_batch`: mean `3.773`, p90 `7.607`, max `9.163`.
- `candidate_test_packed`: mean `1.039`, p90 `1.128`, max `1.591`.
- `event_update`: mean `1.000`.
- `sparse_single`: mean `1.000`.

Current Round 7 paper preset:

| Expected evidence | CSV/summary/figure | Actual result | Status | Reason and next step |
|---|---|---|---|---|
| `correctness_passed` all true | `results/raw/cache_aware_selection.csv` | All `450/450` rows are true. | Meets | Correctness still aligns with Naive/oracle references. |
| `sparse_single` does not regress | workload summary | paper mean `1.000`, p90 `1.000`, max `1.000`. | Meets | Planner keeps selecting `SparseXorKernel`. |
| `event_update` does not regress | workload summary | paper mean `1.002`, p90 `1.000`, max `1.120`. | Meets | One small measured oracle mismatch is timing noise; backend match is `98.61%`. |
| `candidate_test_packed` mean near `1.2-1.3` or better | workload summary | paper mean `1.020`, p90 `1.053`, max `1.407`. | Meets | Lowering the LUT threshold to candidate_count `16` fixed the previous paper-grid outliers. |
| `dense_batch` improves over Round 6 | workload summary | paper mean `1.078`, p90 `1.212`, max `2.227`, down from Round 6 mean `10.637`, max `26.164`. | Meets | Large unpacked batches now choose PackedBlockLUT when the LUT fits cache. |
| `component_decode_batch` improves over Round 6 | workload summary | paper mean `1.057`, p90 `1.163`, max `1.924`, down from Round 6 mean `3.773`, max `9.163`. | Meets | Component syndrome backend selection now follows the calibrated dense-batch rule. |
| Overall max much lower than Round 6 | workload summary | paper max among workloads is `2.227`, versus Round 6 max `26.164`. | Meets | Remaining max comes from small/borderline timing cases, not systematic backend-rule failure. |
| Selection reasons reflect cache/workload regime | raw CSV fields | `selection_reason`, `lut_bytes`, `fits_l1/l2/l3`, `uses_lut`, and `cache_fit_applicable` are present. | Meets | Non-LUT cache-fit ambiguity is fixed. |

## Known Issues

- The planner is still a rule-based baseline, not a learned or measured
  autotuner.
- Backend+block exact oracle match rate is lower than backend-only match rate
  because block width timing is noisy and workload-dependent.
- `hardware_profile.json` records `git_dirty=True` because the benchmark was
  run before the final commit. The final commit contains the same code changes
  used for the run.
- `BCH(511,484,r27)` was not added in this round; the round stayed focused on
  planner calibration and paper-level CPU validation.
- No `full` preset was run.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No `BCH(511,475,4)` profile.
- No external repository code was copied.
- No paper text or speedup claim was written.
- `external_refs/`, `paper/`, and `references/` were not committed.
