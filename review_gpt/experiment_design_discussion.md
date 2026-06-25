# 实验设计讨论：paper-level 主实验与 CacheAwarePlanner 校准

本文件是一次 read-only 实验设计讨论记录。分析基于当前仓库的
`benchmarks/`、`results/raw/*.csv`、`results/summary/*.csv`、
`linear_kernel/cache_aware_planner.py`、`AGENTS.md`，以及本地 `paper/`
下的 notes、参考论文摘要和部分 PDF 文本抽取。没有修改代码，也没有运行新的
benchmark。

## 0. 本轮使用的辅助能力

- `research-experiment-driver`：用于把当前结果转化为可执行的下一轮实验任务。
- `results-analysis`：以 read-only audit 方式检查已有 CSV 的比较单位、统计量和结论边界。
- `paper-figures-advise`：用于选择 ACP 4 页论文里更合适的图表组织方式。
- `pdf`：用于只读检查本地 PDF 论文材料。

重要边界：

- 当前论文定位建议保持为 exact GF(2) component-kernel/backend acceleration。
- 不建议下一轮直接做完整 OFEC decoder、完整 BCH algebraic decoder 或 BER 仿真。
- `cache_aware_selection.csv` 当前是 lightweight，默认 `repeats=1`，只能支持诊断和校准，不适合作为最终 paper-level performance claim。

## 1. 最终 paper-level 实验应该保留哪些？

ACP 4 页论文不适合铺开所有已有 CSV。建议保留 3-4 张主图，加 1 个 correctness / representative summary table。主线应服务三个 claim：

1. 固定 GF(2) 线性 kernel 可以 bit-exact 替换；
2. 不同 workload 下 backend 选择存在明确 regime；
3. cache/LUT footprint 会决定 block-width 和 backend 的取舍。

| 实验名称 | 支撑的论文 claim | 输入规模 | 输出 CSV/图 | 是否必须 |
| ---- | ----------- | ---: | -------- | ---- |
| Bit-exact correctness / component-decoder exactness | 替换 backend 不改变 syndrome、candidate、component-decoder decision；BER/NCG 不变是由 exactness 支撑，而不是重新声称 BER 增益 | `bch_255_239_r16`；all-zero、255 个 single-bit、4096 sampled double-bit、随机 batch；如时间允许 full double-bit `32385` | `component_decoder_exactness.csv`；建议合并成 1 个 correctness table | 必须 |
| Block width latency-memory trade-off | BlockLUT/PackedBlockLUT 是 latency 与 LUT/cache footprint 的 trade-off，不是 block_width 越大越好 | `block_width=4..20 step 2`；`bch_255_239_r16`、`ebch_256_239_r17`、一个 511 profile；batch 建议 `4096`；density `0.05` | `cache_aware.csv` 或专用 paper CSV；Fig: latency + table bytes 双面板 | 必须 |
| Density × batch backend regime map | SparseXor、PackedBlockLUT、PackedBatch 各有适用区间，不能只报单点 speedup | densities `0.001..0.5`；batch `1..16384`；`bch_255_239_r16`/`ebch_256_239_r17` | 新 paper/extended regime CSV；Fig: heatmap 或 facet heatmap | 必须 |
| BCH/eBCH component syndrome / component-loop throughput | 证明不是孤立 microbenchmark，而是 BCH/eBCH component-kernel workload | `total_bits=1e6..1e8` 或 `num_words=4096..262144`；iterations `1,3,5,10` | `bch_syndrome.csv`、`component_loop.csv`；Fig: throughput scaling | 建议必须，若篇幅紧可并入 summary table |
| CacheAwarePlanner vs oracle | planner 的规则选择接近 measured oracle，并可解释 cache footprint | code profiles × cache profiles × workload types；paper preset repeats `>=7` | `cache_aware_selection.csv`；Fig: planner/oracle ratio grouped by workload | 必须，但要先校准 |
| Candidate-count scaling | candidate-heavy workload 中 packed LUT 的作用 | candidate_count `8..16384`；pattern `chase_ii_all` / fixed_weight | `candidate_testing.csv`；Fig: candidate_count vs latency/throughput | 可选，除非论文强调 candidate testing |
| Optical trace workload breakdown | 展示 product/staircase/ofec-like trace 的 kernel-call relevance | workload types `product_like/staircase_like/ofec_like`；num_blocks/window_len sweep | `optical_workloads.csv` / breakdown | 可选；当前不是 full decoder，正文中要谨慎 |

建议最终正文图表：

- Fig. 1：方法/架构图，说明 `f(x)=xA`、backend、planner 与 exactness 边界。
- Fig. 2：block width latency-memory trade-off。
- Fig. 3：density × batch regime map。
- Fig. 4：CacheAwarePlanner vs oracle 或 component-loop throughput，二选一或做双面板。
- Table I：representative summary + exactness table，列出 latency/throughput/memory/correctness。

## 2. CacheAwarePlanner calibration 应该怎么做？

统计来源：`results/raw/cache_aware_selection.csv`，当前 153 行，lightweight，`repeats=1`。因此下表只能用于规则诊断，不能作为最终性能结论。

### 2.1 workload 级别统计

`oracle match rate` 这里按 `selected_backend + selected_block_width` 完全一致计算。

| workload | rows | mean planner/oracle | p90 | max | oracle match rate | backend match rate | 现象 |
|---|---:|---:|---:|---:|---:|---:|---|
| `sparse_single` | 9 | 1.000 | 1.000 | 1.000 | 100.0% | 100.0% | 规则正确，SparseXor 是稳定选择 |
| `candidate_test_packed` | 36 | 1.039 | 1.128 | 1.591 | 72.2% | 97.2% | backend 基本对，block_width 选择偶尔过大 |
| `event_update` | 36 | 1.000 | 1.000 | 1.000 | 97.2% | 97.2% | 规则正确；唯一 mismatch 是 batch=1 的微小计时噪声 |
| `dense_batch` | 36 | 10.637 | 22.853 | 26.164 | 0.0% | 0.0% | 主要问题；规则把大 batch unpacked 输出导向 PackedBatch，但 oracle 多数是 PackedBlockLUT |
| `component_decode_batch` | 36 | 3.773 | 7.607 | 9.163 | 0.0% | 0.0% | 同类问题；component decoder 内部 syndrome backend 用 PackedBlockLUT 更快 |

### 2.2 dense_batch 诊断

按 batch size 看：

| batch_size | rows | mean ratio | max ratio | planner selection | oracle best |
|---:|---:|---:|---:|---|---|
| 1 | 9 | 4.632 | 5.340 | mostly `PackedBlockLUTKernel` | mostly `PackedBatchGF2Kernel` / some `NaiveGF2Kernel` |
| 64 | 9 | 6.605 | 9.871 | `PackedBatchGF2Kernel` | `PackedBlockLUTKernel(10)` |
| 1024 | 9 | 15.931 | 26.164 | `PackedBatchGF2Kernel` | mostly `PackedBlockLUTKernel(8/10)` |
| 4096 | 9 | 15.381 | 23.290 | `PackedBatchGF2Kernel` | `PackedBlockLUTKernel(8/10)` |

判断：

- 不是 cache profile 本身失效，而是规则设计问题。
- 当前规则认为 large unpacked batch 应使用 vectorized `PackedBatchGF2Kernel`。
- 实测中，`PackedBlockLUTKernel.apply_many` 即使输出 unpacked，也通常比 `PackedBatchGF2Kernel.apply_many` 快。
- batch=1 时相反：PackedBlockLUT 的 Python 调用/查表 overhead 不划算，oracle 多为 PackedBatch 或 Naive。

建议规则：

1. 对 `dense_batch` 且 `output_mode=unpacked`：
   - `batch_size < 16`：选择 `PackedBatchGF2Kernel` 或 `NaiveGF2Kernel`，不要选 PackedBlockLUT。
   - `batch_size >= 64` 且 LUT fits L2/L3：选择 `PackedBlockLUTKernel`。
2. `selected_block_width` 不应简单选择 “largest fitting L2/L3”。
   - 对 r<=32 的 Python backend，优先选择 fits L1 的最大 block_width；
   - 如果没有 fits L1，再选择 fits L2 中 table bytes 最小或经验候选 `8`；
   - 不要默认把 `10` 当作最优。

### 2.3 component_decode_batch 诊断

按 batch size 看：

| batch_size | rows | mean ratio | max ratio | planner selection | oracle best |
|---:|---:|---:|---:|---|---|
| 1 | 9 | 2.261 | 2.748 | mostly `PackedBlockLUTKernel` | mostly `PackedBatchGF2Kernel` / some `NaiveGF2Kernel` |
| 64 | 9 | 3.340 | 5.052 | `PackedBatchGF2Kernel` | `PackedBlockLUTKernel(6/8/10)` |
| 1024 | 9 | 4.867 | 9.163 | `PackedBatchGF2Kernel` | `PackedBlockLUTKernel(6/8/10)` |
| 4096 | 9 | 4.626 | 7.939 | `PackedBatchGF2Kernel` | `PackedBlockLUTKernel(6/8/10)` |

判断：

- 同样是规则设计问题，但 ratio 比 dense_batch 小。
- `component_decode_batch` 的 density 是 `0.02`，decoder wrapper 也有额外 Python overhead。
- oracle 仍然明显偏向 PackedBlockLUT，说明 syndrome backend 选择应该与 dense batch 类似。

建议规则：

1. 对 `component_decode_batch`：
   - `batch_size < 16`：选 `PackedBatchGF2Kernel` 或 `NaiveGF2Kernel`。
   - `batch_size >= 64` 且 LUT fits L2/L3：选 `PackedBlockLUTKernel`。
2. 对 block_width：
   - `r=16/17`：默认优先 `8`，除非 calibrated table 显示 `10` 更稳定。
   - `r=32`：默认优先 `8` 或 `10`，但要用 paper preset 重新确认。

### 2.4 candidate_test_packed 诊断

按 batch size 看：

| batch_size / candidate_count | rows | mean ratio | max ratio | 主要 mismatch |
|---:|---:|---:|---:|---|
| 1 | 9 | 1.001 | 1.010 | batch 太小，PackedBatch/Naive 差异接近噪声 |
| 64 | 9 | 1.010 | 1.093 | block_width 偶有 `8` vs `10` |
| 1024 | 9 | 1.106 | 1.591 | planner 常选 `10`，oracle 有时是 `4/6/8` |
| 4096 | 9 | 1.037 | 1.146 | planner 常选 `10`，oracle 常是 `8` |

判断：

- backend 选择基本正确，问题主要是 block_width calibration。
- 当前 `_best_lut_candidate()` 选择 largest fitting L2/L3，导致 `block_width=10` 偏多。
- 对 `bch_255_239_r16`，`block_width=10` 的 table 不 fit L1，最大 ratio 达到 `1.591`。

建议规则：

1. `candidate_test_packed` 保持优先 `PackedBlockLUTKernel`。
2. block_width selection 改为 tiered heuristic：
   - 先找 fits L1 的候选，选其中最大；
   - 如果 batch/candidate_count >= 4096，可在 fits L2 中允许 `10`；
   - 如果 candidate_count 在 `64..1024`，默认选 `8` 更稳；
   - 对 `small_l2_profile` 仍需避免 table 太大。

### 2.5 event_update 诊断

现象：

- 36 行中 planner 36/36 选择 `EventUpdateKernel`。
- oracle 35/36 也是 `EventUpdateKernel`。
- 唯一 mismatch 是 `bch_255_239_r16/default_cpu_cache/batch=1`，ratio 显示 `1.0`，应视为微小计时噪声。

建议规则：

- 保持 `event_update -> EventUpdateKernel`。
- paper-level 图里不要用 batch=1 的 event-update 单点做强结论，应展示 batch>=64 或 flip_count sweep。

### 2.6 sparse_single 诊断

现象：

- 9/9 完全匹配 oracle。
- 规则 `hamming_weight <= sparse_threshold -> SparseXorKernel` 正确。

建议规则：

- 保持当前 sparse threshold。
- 如后续做 regime map，可把 hamming weight / density 与 batch_size 一起 sweep，验证 sparse threshold 是否需要动态化。

## 3. 最终 benchmark grid 应该取多大？

建议引入 3 个 preset：`lightweight`、`paper` 或 `extended`、`full`。

| preset | 用途 | code_profiles | batch_sizes | candidate_counts | block_widths | densities | repeats | 是否加入 511 BCH profile | 预计耗时 |
|---|---|---|---|---|---|---|---:|---|---:|
| `lightweight` | 开发调试、CI、规则 smoke test | `bch_255_239_r16`, `ebch_256_239_r17`, `synthetic_511_r32` | `1,64,1024,4096` | `8,256,4096` | `4,6,8,10` | `0.005,0.05,0.5` | 1-3 | 可不加 | 1-6 分钟，取决于跑哪些脚本 |
| `paper` / `extended` | ACP 主结果 | `bch_255_239_r16`, `ebch_256_239_r17`, `bch_511_484_r27_candidate` 或 `synthetic_511_r32` | `1,4,16,64,256,1024,4096,16384` | `8,32,256,1024,4096,16384` | `4,6,8,10,12,14,16` | `0.001,0.002,0.005,0.01,0.02,0.05,0.1,0.25,0.5` | 7 | 建议加入 `BCH(511,484,3)` candidate | 20-90 分钟 |
| `full` | 可选大规模 sweep / appendix / reviewer backup | 上述全部 + `BCH(511,475,4)` 若实现 r>32 packed | `1..65536` log scale | `8..65536` log scale | `4..20 step 2` | 更密集 density grid | 10-15 | 可加入 `BCH(511,475,4)`，但需扩展 packed output | 数小时到过夜 |

耗时估算依据：

- 当前 `cache_aware_selection --preset lightweight` 约 32 秒，153 行，`repeats=1`。
- 当前 `scripts/run_all_benchmarks.py` 约 5 分钟。
- paper preset 如果把核心 grid 扩到 5-10 倍，并把 repeats 提到 7，单个大脚本可能进入几十分钟量级。

建议不要一次性把所有脚本都扩成 paper preset。更稳妥的做法是：

1. 先扩 `cache_aware_selection` 做 planner calibration；
2. 再扩 `cache_aware` / regime map；
3. 最后只选 1-2 个 component-level throughput benchmark 做 paper result。

## 4. 是否需要新增更真实的 BCH/eBCH profile？

结论：建议加入 `BCH(511,484,3)` candidate profile；`BCH(511,475,4)` 可选但不建议作为下一轮必须项。

### 4.1 为什么值得加 `BCH(511,484,3)`

本地参考论文中，Fougstedt staircase decoder 论文明确使用：

- `BCH(511,484,3)`
- `BCH(511,475,4)`

当前仓库虽然有 `synthetic_511_r32`，但它只是 deterministic random synthetic workload。对 paper reviewer 来说，`n=511` 如果来自真实 BCH profile，会比 synthetic scaling point 更有说服力。

`BCH(511,484,3)` 的优势：

- `r = 511 - 484 = 27`，当前 `PackedBlockLUTKernel` 和 `CacheAwarePlanner` 支持 `r <= 32`，实现成本较低；
- 与 optical staircase/product-like decoder 文献更贴近；
- 可以替代或补强 `synthetic_511_r32` 的 “larger profile” 角色。

### 4.2 怎么生成 matrix

建议沿用现有 clean-room `galois` one-hot systematic encoding 方法：

1. 使用 `galois.BCH(511, 484)` 构造 BCH code；
2. 对每个 message position 输入 one-hot message；
3. encode 得到 systematic codeword；
4. 提取 parity part，得到 message-position contribution；
5. 拼接 parity-position identity，得到 shape `(511, 27)` 的 GF(2) contribution matrix；
6. 标记为 `bch_511_484_r27_candidate`，verification status 为 `candidate`，除非与独立 reference 做过 exact match。

依赖：

- Python `galois` package。当前环境已有 `galois`，测试中也已经使用。
- 需要新增 tests 检查 shape、GF(2) 值、one-hot encode consistency。

### 4.3 `BCH(511,475,4)` 是否现在加入

不建议下一轮立刻做必需项。

原因：

- `r = 36`，超过当前 packed output `r <= 32` 设计边界；
- 若要支持它，需要把 packing 扩到 `uint64` 或 split-packed words；
- 会牵涉 `PackedBlockLUTKernel`、planner、tests、plot、summary 的额外改动；
- 下一轮核心是 planner calibration，不宜扩大 scope。

建议：

- 第 7 轮只加 `BCH(511,484,3)` candidate，或者先只规划不实现；
- `BCH(511,475,4)` 放到后续 “r>32 packed output” 专门轮次。

### 4.4 如果暂时不加真实 511 profile，论文如何解释

如果短期只保留 `synthetic_511_r32`，必须明确写：

- 它不是 real BCH profile；
- 它只用于 stress-test larger output width and LUT/cache scaling；
- paper claim 主要基于 `bch_255_239_r16` 和 `ebch_256_239_r17`；
- 不能把 synthetic profile 说成 optical-FEC 标准参数。

## 5. 候选图表如何设计？

| 图表 | 类型 | 数据来源 | 是否必须 | 设计建议 |
|---|---|---|---|---|
| Fig. 1 Backend architecture | schematic | 代码结构，不来自 CSV | 必须 | 展示 `f(x)=xA`、SparseXor、PackedBlockLUT、PackedBatch、EventUpdate、CacheAwarePlanner；不要塞性能数字 |
| Fig. 2 Block-width latency-memory trade-off | 双面板 line plot | `cache_aware.csv` 或 paper block-width CSV | 必须 | 左：latency；右：table bytes；加 error bar；legend 放外侧；标注 cache-tier 线 |
| Fig. 3 Density × batch regime map | heatmap/facet | paper preset regime CSV | 必须 | cell 表示 oracle best backend 或 planner/oracle ratio；每个 code profile 一个 panel |
| Fig. 4 Planner vs oracle | grouped bar / boxplot | calibrated `cache_aware_selection.csv` | 必须 | y 轴 `planner_over_oracle`；横线 1.0；按 workload 分组；显示 p90 或 error bar |
| Candidate-count scaling | line plot | `candidate_testing.csv` | 可选 | 如果论文讲 candidate-heavy workload，则保留；否则放 appendix/review material |
| Optical trace breakdown | stacked bar / grouped bar | `optical_workloads.csv`, breakdown | 可选 | 仅作为 kernel-call relevance，不要称为 full decoder |
| Exactness table | table | `component_decoder_exactness.csv` + correctness tests | 必须 | 列出 mismatch=0、sample/full coverage、profile、backend |

建议删减：

- 不建议正文同时放 `batch_crossover`、`density_backend_comparison`、`planner_comparison`、`stream_throughput` 等所有历史图。它们适合内部 review，不适合 ACP 4 页主线。
- `optical trace breakdown` 如果没有 full decoder，就不要放在最核心位置，可作为支持性结果。

## 6. 实验耗时预估

| preset | 预计命令 | 预计耗时 | 风险 |
| ------ | ---- | ---: | -- |
| planner calibration lightweight | `python -m benchmarks.bench_cache_aware_selection --preset lightweight --repeats 3` + summary/plot | 2-5 分钟 | 仍然不够 paper claim，只能看规则方向 |
| planner calibration paper | `python -m benchmarks.bench_cache_aware_selection --preset paper --repeats 7` | 10-30 分钟 | 需要先实现 paper preset；candidate/component rows 较慢 |
| selected paper-level benchmark | block-width + regime map + component-loop/syndrome + exactness | 20-90 分钟 | 如果 grid 太大，Python overhead 和内存分配会放大；需要分脚本保存 |
| full sweep | `python scripts/run_all_benchmarks.py --preset full` 或分脚本 full | 数小时到过夜 | 失败恢复、CSV 覆盖、温度/后台进程波动、无 CI 时间保障 |

建议执行策略：

- 第 7 轮不要跑 full。
- 第 7 轮只跑 calibration lightweight/paper-small。
- 真正 paper-level benchmark 放在第 8 轮，且先固定 grid 和 figure list。

## 7. 补实验第 7 轮建议

必须做：

1. 校准 `CacheAwarePlanner` 的 dense/component 规则。
   - `dense_batch` / `component_decode_batch`：
     - `batch_size < 16`：选 `PackedBatchGF2Kernel` 或 `NaiveGF2Kernel`；
     - `batch_size >= 64` 且 LUT fits L2/L3：选 `PackedBlockLUTKernel`；
     - 不要因为 `output_mode=unpacked` 就强制走 `PackedBatchGF2Kernel`。
2. 校准 block_width 选择。
   - 把 “largest fitting L2/L3” 改成 cache-tier aware：
     - 优先 largest fits L1；
     - 其次 fits L2 中的经验候选 `8` 或最小 table bytes；
     - candidate_count 很大时才允许 `10/12`。
3. 增加 planner unit tests。
   - dense batch `batch_size=64/1024` 应选择 `PackedBlockLUTKernel`；
   - component decode batch `batch_size=64/1024` 应选择 `PackedBlockLUTKernel`；
   - batch=1 不应盲选 PackedBlockLUT；
   - event_update 和 sparse_single 规则保持不变。
4. 增加 `cache_aware_selection` 的 `paper` 或 `extended` preset。
   - 至少支持 `--preset paper`、`repeats=7`；
   - 先保持 grid 适中，不要一次扩到 full。
5. 更新 summary。
   - 输出 workload 级 mean/p90/max `planner_over_oracle`；
   - 输出 exact oracle match rate 和 backend-only match rate；
   - 标记 correctness 全 True。
6. 更新 Round 7 review_gpt。
   - 明确校准前后 dense/component 的 ratio 是否下降；
   - 若仍不理想，说明是 Python overhead、rule 还是 measurement noise。

可选做：

1. 加入 `bch_511_484_r27_candidate`。
   - 如果加入，限定为 `galois` candidate profile；
   - 暂不做 `BCH(511,475,4)`，避免 r>32 scope 膨胀。
2. 增加 regime-map figure prototype。
   - 只生成 diagnostic 版本，不重构所有 paper figures。
3. 增加 calibration audit CSV。
   - 记录 selected/oracle mismatch reason，便于后续调规则。

验收标准：

1. `python -m pytest -q` 通过。
2. `python -m benchmarks.bench_cache_aware_selection --preset lightweight` 通过。
3. 如实现 paper preset，`python -m benchmarks.bench_cache_aware_selection --preset paper` 在可接受时间内跑通。
4. `correctness_passed=True` 全部成立。
5. `dense_batch` 和 `component_decode_batch` 的 mean/p90 `planner_over_oracle` 相比当前 lightweight 明显下降。
6. `candidate_test_packed`、`event_update`、`sparse_single` 不出现回退。
7. review_gpt 中如实记录：哪些符合预期、哪些仍不符合、是否仍不能写 final performance claim。

需要先讨论再动手的问题：

1. 第 7 轮是否同时加入 `bch_511_484_r27_candidate`？
   - 我建议可以加，但如果想让第 7 轮专注 planner calibration，也可以推迟到第 8 轮。
2. `NaiveGF2Kernel` 是否应该成为 planner 可选 backend？
   - 当前 planner 主要选 Sparse/PackedBatch/PackedBlockLUT/EventUpdate；但 batch=1 的 dense/component oracle 偶尔是 Naive。
   - 若要完全追 oracle，planner 需要允许 small-batch dense 选择 Naive。
   - 若为了简化 paper story，也可以把 small-batch dense 统一归为 “not target regime”。
3. paper 主图是否保留 candidate-testing？
   - 如果主线是 exact component kernel backend，candidate-testing 可以作为 supporting workload；
   - 如果篇幅紧，优先保留 block-width、regime map、planner-vs-oracle、exactness table。
