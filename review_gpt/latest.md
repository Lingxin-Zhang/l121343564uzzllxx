# Latest Review Summary

Current round: supplemental experiment round 6.

## Goal

Implement cache-aware backend/block-width selection and validate it with a
lightweight benchmark. This round adds a rule-based `CacheAwarePlanner`, a
selection benchmark that compares planner choices against an oracle best
measured backend, a summary CSV, and a diagnostic figure.

This round does not add BER, a full OFEC decoder, a full BCH algebraic decoder,
or paper conclusions.

## Skills Used

- `superpowers:test-driven-development`: used for the initial red/green flow
  around planner and benchmark tests.
- `superpowers:verification-before-completion`: used before claiming test,
  benchmark, and push status.
- `plot-from-data`: considered for publication plotting workflow; direct
  templates were not used because this round needed a small project-local
  diagnostic matplotlib figure.
- Git/GitHub publish workflow: local `git` is used for the required commit and
  push. No PR is opened because this repository workflow pushes directly to the
  configured remote branch.

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
- Refreshed CSV/summary/figure artifacts under `results/` through the requested
  benchmark commands and `scripts/run_all_benchmarks.py`.

## Implementation Notes

- `CacheAwarePlanner` records matrix shape, cache profile, block-width
  candidates, and LUT footprint estimates.
- Planner output includes:
  - `selected_backend`
  - `selected_block_width`
  - `lut_bytes`
  - `fits_l1`
  - `fits_l2`
  - `fits_l3`
  - `selection_reason`
- Current rule baseline:
  - `event_update` selects `EventUpdateKernel`.
  - low-weight single inputs select `SparseXorKernel`.
  - packed candidate batches select `PackedBlockLUTKernel` when the LUT fits
    cache and the batch is large enough.
  - large unpacked batches use `PackedBatchGF2Kernel` as a conservative
    vectorized fallback unless the small-batch LUT rule applies.
- `benchmarks/bench_cache_aware_selection.py` covers:
  - code profiles: `bch_255_239_r16`, `ebch_256_239_r17`,
    `synthetic_511_r32`
  - cache profiles: `default_cpu_cache`, `small_l2_profile`,
    `large_l3_profile`
  - workloads: `sparse_single`, `dense_batch`, `candidate_test_packed`,
    `component_decode_batch`, `event_update`
  - batch sizes: `1`, `64`, `1024`, `4096`
  - block widths: `4`, `6`, `8`, `10`
- For each case, the benchmark validates correctness against a Naive reference,
  times the selected backend and all candidates, and records the oracle best.

## Verification

- `python -m pytest -q`
  - Result: `280 passed, 1 skipped, 23 warnings`.
- `python -m benchmarks.bench_cache_aware_selection --preset lightweight`
  - Result: passed and wrote `results/raw/cache_aware_selection.csv`.
- `python scripts/summarize_results.py`
  - Result: passed and wrote `results/summary/cache_aware_selection_summary.csv`.
- `python scripts/plot_experiment_round06_results.py`
  - Result: passed and wrote Round 6 PNG/PDF figures.
- `python scripts/run_all_benchmarks.py`
  - Result: passed, including the new Round 6 benchmark and figure step.

## Artifact Checks

- `results/raw/cache_aware_selection.csv`: 153 rows.
- `results/summary/cache_aware_selection_summary.csv`: 153 rows.
- `results/figures/experiment_round06_cache_aware_selection.png`: generated.
- `results/figures/experiment_round06_cache_aware_selection.pdf`: generated.
- `correctness_passed=True` for all 153 rows.
- Empty selected backend/reason rows: 0.
- Non-positive or non-finite `planner_over_oracle` rows: 0.
- Overall `planner_over_oracle`: mean `3.929`, max `26.164`.
- Candidate workload:
  - planner selected `PackedBlockLUTKernel` in 27/36 rows.
  - oracle best was `PackedBlockLUTKernel` in 27/36 rows.
  - mean `planner_over_oracle` was about `1.039`.
- Event-update workload:
  - planner selected `EventUpdateKernel` in 36/36 rows.
  - oracle best was `EventUpdateKernel` in 35/36 rows.
- Sparse-single workload:
  - planner selected `SparseXorKernel` in 9/9 rows.
  - oracle best was `SparseXorKernel` in 9/9 rows.

## 实验结果是否符合论文预期

| 预期证据 | 对应 CSV/summary/figure | 实际结果 | 是否符合 | 原因与下一步 |
|---|---|---|---|---|
| planner 真的使用 cache footprint 做选择 | `results/raw/cache_aware_selection.csv` fields `lut_bytes`, `fits_l1`, `fits_l2`, `fits_l3`, `selection_reason` | All rows include footprint fields and non-empty selection reasons; LUT rows record selected block width and cache-fit flags. | 符合 | Current planner is rule-based, not learned or oracle-tuned. |
| selected backend 接近 oracle best | `planner_over_oracle` in raw and summary CSV; Round 6 figure | Sparse/event workloads are at or near oracle parity. Candidate workload mean ratio is about `1.039`. Dense/component workloads are worse, with overall max `26.164`. | 部分符合 | Dense/component rules are conservative and often choose `PackedBatchGF2Kernel`; measured Python implementation often favors `PackedBlockLUTKernel`. Next step is calibration or revised rules for large unpacked batches. |
| PackedBlockLUT 在 candidate-heavy 且 cache fit 时有优势 | `candidate_test_packed` rows in raw CSV | Planner and oracle both use `PackedBlockLUTKernel` in 27/36 candidate rows; candidate mean ratio is close to 1. | 符合 | Small batch or cache-fit edge cases still fall back to vectorized baselines. |
| EventUpdate 在 update workload 中被正确选择 | `event_update` rows in raw CSV | Planner selected `EventUpdateKernel` in 36/36 rows; oracle selected it in 35/36 rows. | 符合 | One row had a different measured oracle best, likely timing noise or tiny workload effects. |
| 结果不符合时能定位原因 | raw CSV, summary CSV, Round 6 figure | Dense and component-decode batch ratios show the main gap. | 符合 | Likely causes are Python overhead, benchmark scale, and planner rules that prefer vectorized fallback for large unpacked batches. |

## Known Issues

- `CacheAwarePlanner` is an explainable baseline, not an optimal scheduler.
- Dense/component-decode batch selection is not yet close to oracle in the
  lightweight benchmark.
- Timing is Python-level and may be sensitive to small workload noise.
- The Round 6 figure is diagnostic; it is not a final paper-style plot.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No full product-code or staircase-code decoder.
- No paper text or speedup claim.
- No external repository code was copied.
- `external_refs/`, `paper/`, and `references/` were not committed.
