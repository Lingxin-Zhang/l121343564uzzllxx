# Supplemental Experiment Round 6 Summary

## Goal

Add cache-aware backend/block-width selection. The round implements an
explainable rule-based planner, benchmarks planner choices against measured
oracle candidates, exports CSV/summary/figure artifacts, and records where the
planner currently matches or misses oracle behavior.

## Modified Files

- `linear_kernel/cache_aware_planner.py`
- `linear_kernel/__init__.py`
- `benchmarks/bench_cache_aware_selection.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round06_results.py`
- `scripts/run_all_benchmarks.py`
- `tests/test_cache_aware_planner.py`
- `tests/test_cache_aware_selection_benchmark.py`
- `tests/test_result_summary.py`
- `README.md`
- `AGENTS.md`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_06_summary.md`
- Refreshed generated CSV/summary/figure artifacts under `results/`.

## Implementation Summary

- Added `CacheAwarePlanner` and `CacheAwareSelection`.
- Planner decisions include backend, block width, LUT bytes, L1/L2/L3 fit
  flags, and an explanatory selection reason.
- Added `benchmarks/bench_cache_aware_selection.py`.
- The benchmark covers three code profiles, three cache profiles, five workload
  types, four batch sizes, and four block-width candidates.
- Each benchmark row validates correctness against a Naive reference and records
  both planner-selected runtime and measured oracle-best runtime.
- Added `cache_aware_selection_summary.csv` support in `scripts/summarize_results.py`.
- Added Round 6 diagnostic figure export:
  - `results/figures/experiment_round06_cache_aware_selection.png`
  - `results/figures/experiment_round06_cache_aware_selection.pdf`
- Added the new benchmark and figure script to `scripts/run_all_benchmarks.py`.

## Verification

- `python -m pytest -q`
  - `280 passed, 1 skipped, 23 warnings`
- `python -m benchmarks.bench_cache_aware_selection --preset lightweight`
  - passed
- `python scripts/summarize_results.py`
  - passed
- `python scripts/plot_experiment_round06_results.py`
  - passed
- `python scripts/run_all_benchmarks.py`
  - passed

## Artifact Checks

- `results/raw/cache_aware_selection.csv`: 153 rows.
- `results/summary/cache_aware_selection_summary.csv`: 153 rows.
- Round 6 PNG and PDF figures were generated.
- All `correctness_passed` values are `True`.
- No selected backend or selection reason is empty.
- All `planner_over_oracle` values are positive finite numbers.

## 实验结果是否符合论文预期

| 预期证据 | 对应 CSV/summary/figure | 实际结果 | 是否符合 | 原因与下一步 |
|---|---|---|---|---|
| planner 使用 cache footprint 做选择 | `cache_aware_selection.csv`, `cache_aware_selection_summary.csv` | Rows contain `lut_bytes`, cache-fit flags, selected block width, and reason strings. | 符合 | The rule baseline is transparent and reproducible. |
| selected backend 接近 oracle best | `planner_over_oracle`, Round 6 figure | Overall mean ratio is `3.929`; sparse/event/candidate cases are close, dense/component cases are not. | 部分符合 | Need calibration or rule tuning for large unpacked dense/component batches. |
| PackedBlockLUT 在 candidate-heavy 且 cache fit 时有优势 | `candidate_test_packed` rows | Planner and oracle both use `PackedBlockLUTKernel` in 27/36 rows; candidate mean ratio is about `1.039`. | 符合 | Remaining rows are small-batch or cache-edge cases. |
| EventUpdate 在 update workload 中被正确选择 | `event_update` rows | Planner selects `EventUpdateKernel` in 36/36 rows; oracle chooses it in 35/36 rows. | 符合 | One oracle mismatch is likely tiny timing/noise effect. |
| 不符合预期时能解释原因 | raw CSV, summary CSV, Round 6 figure | Dense/component workloads expose the main planner gap. | 符合 | Python overhead and conservative vectorized fallback rules are the likely causes. |

## Skills Used

- `superpowers:test-driven-development`
- `superpowers:verification-before-completion`
- `plot-from-data` was checked, but project-local plotting was more appropriate
  for this diagnostic figure.
- Git/GitHub publish workflow was followed with local `git commit` and push.

## Known Issues

- The planner is a deterministic rule baseline, not an oracle optimizer.
- Dense/component-decode batch rules need tuning before making any paper-level
  claim.
- This round produces a diagnostic figure only.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No external repository code copied.
- No paper conclusion or speedup claim.
- `external_refs/`, `paper/`, and `references/` were not committed.
