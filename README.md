# fec_linear_backend

面向 ACP 2026 光通信 FEC 短论文的 Python 实验仓库，用于实现和评估 exact GF(2) linear-kernel acceleration backend。

## 论文目标

本项目关注光通信 FEC 仿真和译码流程中反复出现的固定 GF(2) 线性内核：

```text
f(x) = xA, x, A in GF(2)
```

目标不是提出新的 BCH/eBCH 编码算法，也不是改变译码决策或提升 BER，而是在 syndrome computation、parity generation、candidate error-pattern testing 和少量 bit flip 后的 syndrome update 等场景中，比较多个 bit-exact backend 的 runtime。

## 为什么是光通信 FEC

高速光通信中的 product-like、staircase 和 oFEC 结构会大量重复调用 BCH/eBCH component code。即使每次调用的数学定义不变，固定矩阵上的 GF(2) 线性操作仍可能成为仿真和译码循环中的热点。因此，本仓库聚焦 workload-aware backend selection，而不是码构造本身。

## 为什么关注 fixed GF(2) linear kernels

在固定码参数下，许多 component-code 操作都可以抽象为固定二元矩阵乘法或其增量更新。不同 workload 的最优执行方式可能不同：稀疏输入、批量输入、cache 友好的 block-LUT、packed batch 或 event-driven update 都可能在不同条件下更合适。

## 后续计划实现的 backend

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `PackedBatchGF2Kernel`
- `EventUpdateKernel`
- `HybridPlanner`

所有 backend 后续都必须与 `NaiveGF2Kernel` 做 bit-exact correctness test。

## 仓库结构

```text
linear_kernel/   GF(2) linear-kernel backend skeleton
codes/           BCH/eBCH-like component-code parameter placeholders
decoders/        BDD/decode-LUT placeholder interfaces
benchmarks/      后续 benchmark 入口
scripts/         benchmark orchestration 和 plotting 脚本
tests/           correctness test skeleton
results/         raw CSV 和论文图输出目录
paper/           ACP 短论文草稿和研究 notes
references/      文献 PDF、BibTeX、综述和边界说明
```

## 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## 后续测试和 benchmark

当前只有 skeleton。后续实现 backend 后，计划使用：

```bash
pytest
bash scripts/run_all_benchmarks.sh
python scripts/plot_results.py
```

benchmark 必须固定 random seed，使用 `time.perf_counter()`，包含 warmup 和多次重复，输出 mean/std，并保存 CSV 到 `results/raw/`、图到 `results/figures/`。

## 当前状态

当前已实现并测试：

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `EventUpdateKernel`
- 最小 correctness 测试

尚未实现：

- `PackedBatchGF2Kernel`
- `HybridPlanner`
- benchmark
- 实验结果或论文图
