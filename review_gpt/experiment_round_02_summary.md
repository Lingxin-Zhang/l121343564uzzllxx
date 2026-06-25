# 补实验第 2 轮总结

## 范围

本轮完成：

- 补实验第 1 轮小修
- candidate error-pattern testing benchmark
- product_like / staircase_like / ofec_like trace-level workload benchmark
- event update 融入 trace-level workload
- summary CSV
- diagnostic figures
- tests

本轮没有写论文正文，没有做 BER，没有实现完整 decoder。

## 修改文件

- `workloads/__init__.py`
- `workloads/candidate_patterns.py`
- `workloads/optical_traces.py`
- `benchmarks/bench_candidate_testing.py`
- `benchmarks/bench_optical_workloads.py`
- `benchmarks/bench_cache_aware.py`
- `benchmarks/bench_code_profiles.py`
- `codes/code_profiles.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round02_results.py`
- `scripts/run_all_benchmarks.py`
- `scripts/run_all_benchmarks.sh`
- `tests/test_candidate_patterns.py`
- `tests/test_candidate_testing.py`
- `tests/test_optical_workload_trace.py`
- `tests/test_round2_cache_fields.py`
- `tests/test_benchmark_correctness_failfast.py`
- `tests/test_code_profiles.py`
- `tests/test_round2_benchmark_tools.py`
- `README.md`
- `AGENTS.md`
- `docs/reference_inspection_notes.md`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_02_summary.md`

## 实现内容

- 新增 deterministic candidate pattern 生成：
  - Chase-II style all-combination masks
  - fixed-weight sparse masks
- 新增 candidate syndrome benchmark：
  - `Naive.apply_many`
  - `SparseXor.apply_many`
  - `PackedBatch.apply_many`
  - `PackedBlockLUT.apply_many_packed`
  - `EventUpdate.from_zero`
  - `HybridPlanner.apply_many_packed`
- 新增 trace-level workload benchmark：
  - `product_like`
  - `staircase_like`
  - `ofec_like`
  - method includes `EventUpdate.integrated`
- 修补 cache-aware metadata：
  - cache profile
  - matrix shape
  - packed dtype
  - LUT block metadata
  - cache size metadata
- `CodeProfile` 新增 `verification_status`，避免把 eBCH-like candidate 或 synthetic workload 写成标准矩阵。
- correctness mismatch 现在会 fail fast。

## 生成结果

Raw CSV：

- `results/raw/cache_aware.csv`
- `results/raw/code_profile_scaling.csv`
- `results/raw/candidate_testing.csv`
- `results/raw/optical_workloads.csv`

Summary CSV：

- `results/summary/cache_aware_summary.csv`
- `results/summary/code_profile_scaling_summary.csv`
- `results/summary/candidate_testing_summary.csv`
- `results/summary/optical_workloads_summary.csv`

Figures：

- `results/figures/experiment_round02_candidate_testing.png`
- `results/figures/experiment_round02_candidate_testing.pdf`
- `results/figures/experiment_round02_optical_workloads.png`
- `results/figures/experiment_round02_optical_workloads.pdf`

## 验证

- `python -m pytest -q`
  - `249 passed, 1 skipped`
- `python -m benchmarks.bench_cache_aware --preset lightweight`
  - passed
- `python -m benchmarks.bench_code_profiles --preset lightweight`
  - passed
- `python -m benchmarks.bench_candidate_testing --preset lightweight`
  - passed
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - passed
- `python scripts/summarize_results.py`
  - passed
- `python scripts/plot_experiment_round02_results.py`
  - passed
- `python scripts/run_all_benchmarks.py`
  - passed, about 4 minutes

## 已知问题

- 当前 candidate testing 和 workload trace 仍是 Python-level lightweight benchmark。
- `EventUpdate.from_zero` 是 correctness-oriented loop path，不是最终优化实现。
- `ofec_like` 是 component-kernel workload trace，不是标准 OFEC decoder。
- lightweight 结果只能用于诊断和 review，不能写成论文结论。

## 下一步建议

- 下一轮可以扩大 candidate/testing workload 的点数和 repeats。
- 可以把 `EventUpdate.integrated` 拆成更明确的 subtask timing。
- 可以增加更正式的 cache/regime map，但仍需避免把 synthetic workload 说成真实标准。
