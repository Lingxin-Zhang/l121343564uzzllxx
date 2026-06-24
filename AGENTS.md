# AGENTS.md

## 项目目标

本仓库服务于一篇 ACP 2026 光通信 FEC 短论文。目标是实现并评估 exact GF(2) linear-kernel acceleration backend，用于降低光通信 FEC 仿真和 component-code 译码循环中的 runtime。

核心抽象是：

```text
f(x) = xA, x, A in GF(2)
```

本项目不是新的 BCH/eBCH 编码算法，不是新的 BCH/eBCH 译码算法，也不声称提升 BER。

## 方法边界

后续 agent 必须遵守：

- 不改变 BCH/eBCH 编码定义。
- 不改变 BCH/eBCH 译码输出。
- 不改变 BER。
- 所有 backend 必须 bit-exact 等价。
- `BlockLUTKernel` 只是一个 backend primitive，不是唯一贡献。
- 论文重点是 optical FEC workload 下的 hybrid execution 和 workload-aware backend selection。
- 如后续参考 `D:\PKU\OFEC\project\ofec-0.1.0` 的参数、公式或实现逻辑，必须写明：“参考 OFEC_CNN 的参数/逻辑，本仓库重新实现”。
- 不要直接复制 OFEC_CNN 的大段代码，不要复用 OFEC_CNN 的工程结构作为本仓库主结构。

## Backend 当前状态

已实现：

1. `NaiveGF2Kernel`
2. `SparseXorKernel`
3. `BlockLUTKernel`
4. `EventUpdateKernel`

尚未实现：

1. `PackedBatchGF2Kernel`
2. `HybridPlanner`

## 正确性优先

每个 backend 后续都必须和 `NaiveGF2Kernel` 做 correctness test。至少覆盖：

- random input；
- different input densities；
- batch input；
- event update；
- different block widths；
- packed/unpacked consistency。

不得在 correctness test 缺失时报告 speedup 或论文结论。

## Benchmark 规范

后续所有 benchmark 必须：

- 固定 random seed；
- 使用 `time.perf_counter()`；
- 包含 warmup；
- 重复多次；
- 输出 mean 和 std；
- 保存 CSV 到 `results/raw/`；
- 保存图到 `results/figures/`；
- 在 README 中写清楚复现命令。

## 每轮提交规范

每次修改后必须在 `review_gpt/` 中写总结。总结内容包括：

- 修改文件；
- 功能说明；
- 测试结果；
- 已知问题；
- 下一步建议。

每轮总结必须更新 `review_gpt/latest.md`，并新建对应的 `review_gpt/round_xx_summary.md`。修改完成后必须 `git commit`，并 push 到远程仓库 `Lingxin-Zhang/l121343564uzzllxx`。不要只在本地改代码不推送。

如果环境中有适合的 agent skill，例如 Python 项目、pytest、Markdown 文档、Git/GitHub 相关、论文实验实现/论文写作相关skill，请优先使用这些 skill 完成任务。

## 画图规范

后续所有图都要适合 IEEE/ACP 双栏论文：

- 字体清楚；
- 坐标轴单位明确；
- legend 不遮挡；
- 同时保存 `.pdf` 和 `.png`；
- 图名和 CSV 文件名对应；
- 使用 matplotlib，不要引入复杂画图库。

## 严禁夸大

禁止使用这些表述：

- “首次提出线性码 block-LUT 编码器”
- “首次提出 BCH LUT encoder”
- “提升 BER”
- “改变 BCH 纠错性能”
- “替代所有 BCH decoder”

推荐使用这些安全表述：

- exact GF(2) linear-kernel backend
- bit-exact acceleration
- workload-aware backend selection
- cache-aware block-LUT execution
- runtime reduction without changing decoding decisions
- optical FEC simulation/decoding acceleration
