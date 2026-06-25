# Latest Review Summary

当前轮次：补实验第 2 轮

## 本轮结论

本轮完成了补实验第 2 轮的代码闭环：先修补补实验第 1 轮的小缺口，然后新增 candidate error-pattern testing benchmark 和 trace-level product_like / staircase_like / ofec_like workload benchmark，并生成对应 raw CSV、summary CSV 和 diagnostic figures。

仓库旧记录名：`review_gpt/round_18_summary.md`

对应：补实验第 1 轮

## 是否完成补实验第 1 轮小修

已完成。

- `results/raw/cache_aware.csv` 已补全 cache/profile metadata 字段。
- `benchmarks/bench_cache_aware.py` 已支持 CLI cache override：
  - `--l1d-kb`
  - `--l2-kb`
  - `--l3-mb`
  - `--cache-line`
- `benchmarks/bench_cache_aware.py` 和 `benchmarks/bench_code_profiles.py` 已改为 correctness mismatch 直接 raise。
- `CodeProfile` 新增 `verification_status`：
  - `bch_255_239_r16`: `verified_candidate`
  - `ebch_256_239_r17`: `candidate_unverified`
  - synthetic profiles: `synthetic_workload`
- `code_profile_scaling.csv` 已补充 profile verification metadata。

## 新增 candidate testing benchmark

已新增：

- `workloads/candidate_patterns.py`
- `benchmarks/bench_candidate_testing.py`

支持：

- `chase_ii_all`
- `fixed_weight`
- `--preset lightweight`
- `--preset full`

所有 backend 输出都先和 Naive reference 对齐；如果不一致会 raise，不写假 CSV。

## 新增 trace-level workload benchmark

已新增：

- `workloads/optical_traces.py`
- `benchmarks/bench_optical_workloads.py`

支持：

- `product_like`
- `staircase_like`
- `ofec_like`

这些 workload 只是 component-kernel trace，不是完整 decoder，不包含 BER。

## 生成的 raw CSV

- `results/raw/cache_aware.csv`
- `results/raw/code_profile_scaling.csv`
- `results/raw/candidate_testing.csv`
- `results/raw/optical_workloads.csv`

本轮 `scripts/run_all_benchmarks.py` 也刷新了已有 lightweight raw CSV。

## 生成的 summary CSV

- `results/summary/cache_aware_summary.csv`
- `results/summary/code_profile_scaling_summary.csv`
- `results/summary/candidate_testing_summary.csv`
- `results/summary/optical_workloads_summary.csv`
- `results/summary/best_backend_by_workload.csv`

## 生成的 figures

- `results/figures/experiment_round02_candidate_testing.png`
- `results/figures/experiment_round02_candidate_testing.pdf`
- `results/figures/experiment_round02_optical_workloads.png`
- `results/figures/experiment_round02_optical_workloads.pdf`

本轮 `scripts/run_all_benchmarks.py` 也刷新了已有 diagnostic figures。

## 测试与运行结果

- `python -m pytest -q`
  - 结果：`249 passed, 1 skipped`
- `python -m benchmarks.bench_cache_aware --preset lightweight`
  - 结果：通过，生成 `results/raw/cache_aware.csv`
- `python -m benchmarks.bench_code_profiles --preset lightweight`
  - 结果：通过，生成 `results/raw/code_profile_scaling.csv`
- `python -m benchmarks.bench_candidate_testing --preset lightweight`
  - 结果：通过，生成 `results/raw/candidate_testing.csv`
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - 结果：通过，生成 `results/raw/optical_workloads.csv`
- `python scripts/summarize_results.py`
  - 结果：通过，生成/刷新 summary CSV
- `python scripts/plot_experiment_round02_results.py`
  - 结果：通过，生成补实验第 2 轮 diagnostic figures
- `python scripts/run_all_benchmarks.py`
  - 结果：通过；运行时间约 4 分钟；已执行新增 lightweight benchmark、summary 和 diagnostic plotting

## 提交与推送状态

- 本地 commit 已创建。
- push 首次尝试失败：`curl 56 Recv failure: Connection was reset`。
- push 第二次尝试失败：无法连接 `github.com:443`。
- push 第三次尝试失败：无法连接 `github.com:443`。
- 后续重试已成功 push 到 `origin/main`。

## CSV 抽查

- `cache_aware.csv`: 972 rows，`correctness_passed=True`
- `code_profile_scaling.csv`: 48 rows，`correctness_passed=True`
- `candidate_testing.csv`: 180 rows，`correctness_passed=True`
- `optical_workloads.csv`: 192 rows，`correctness_passed=True`
- `candidate_testing_summary.csv`: 180 rows，`correctness_all_true=True`
- `optical_workloads_summary.csv`: 192 rows，`correctness_all_true=True`

## 外部参考仓库

本轮没有复制外部代码。

本轮没有提交 `external_refs/`。

本轮没有把真实本地路径写入 tracked 文件。

本轮新增了 `docs/reference_inspection_notes.md`，只记录 reference-only / clean-room policy 与 trace 设计含义。

## 明确未做

- 是否复制外部代码：no
- 是否做 BER：no
- 是否实现完整 OFEC decoder：no
- 是否实现完整 BCH algebraic decoder：no
- 是否实现完整 Chase-Pyndiah decoder：no
- 是否编造 speedup 结论：no
- 是否把 lightweight benchmark 当作最终论文结论：no
- 是否改变 placeholder matrix 语义：no

## 当前进度估计

补实验主线完成约 65%。

## 接下来还剩几轮

预计还剩 2 轮主线 + 1 个可选机动轮。
