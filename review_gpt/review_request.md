# Review Request: Skeleton Initialization

## 本轮实现内容

本轮根据用户 prompt 初始化了一个干净的 Python 实验仓库，用于支撑 ACP 2026 光通信 FEC 方向短论文。范围严格限制为：

- 项目结构初始化；
- `AGENTS.md`；
- `README.md`；
- paper notes；
- references notes；
- Python package skeleton；
- 最小 import 测试。

未实现完整 backend、未跑 benchmark、未生成结果图、未编造 speedup 或 BER 结论。

## 关键项目边界

本项目目标是 exact GF(2) linear-kernel acceleration backend，用于 optical FEC simulation/decoding acceleration。

必须避免以下说法：

- “首次提出线性码 block-LUT 编码器”
- “首次提出 BCH LUT encoder”
- “提升 BER”
- “改变 BCH 纠错性能”
- “替代所有 BCH decoder”

允许的安全表述包括：

- exact GF(2) linear-kernel backend
- bit-exact acceleration
- workload-aware backend selection
- cache-aware block-LUT execution
- runtime reduction without changing decoding decisions
- optical FEC simulation/decoding acceleration

## 已创建的主要文件

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `requirements.txt`
- `linear_kernel/*.py`
- `codes/*.py`
- `decoders/*.py`
- `benchmarks/*.py`
- `scripts/*.py`
- `tests/test_correctness.py`
- `paper/draft/main.tex`
- `paper/notes/*.md`
- `references/README.md`
- `references/summaries/*.md`

## Review GPT 请重点检查

1. `AGENTS.md` 是否充分约束了后续 coding agent，尤其是论文边界、正确性优先、benchmark 规范和禁止夸大。
2. `README.md` 是否准确表达当前项目状态：仅 skeleton，尚无完整实现和实验结果。
3. Python package skeleton 是否可维护，类名和文件名是否与后续 backend 规划一致。
4. 是否存在任何可能被误解为已经完成实验、已经取得 speedup、或已经证明 BER 不变的表述。
5. `paper/notes/novelty_boundary.md` 是否足够明确地区分已有 partitioned LUT / CRC slicing / M4RI/Four Russians 与本项目贡献。
6. 是否需要增加 `.gitignore`、`LICENSE`、`docs/` 或 `.pipeline/` 等辅助文件。

## 已做验证

在仓库根目录运行过：

```bash
python -m pytest tests/test_correctness.py -q
```

结果：

```text
1 passed
```

也做过直接 import 验证：

```bash
python -c "from linear_kernel import NaiveGF2Kernel, SparseXorKernel, BlockLUTKernel, PackedBatchGF2Kernel, EventUpdateKernel, HybridPlanner; from codes import BCHLikeCode, EBCHLikeCode; from decoders import BDDLUTDecoder; print('imports-ok')"
```

结果：

```text
imports-ok
```

## OFEC_CNN 参考路径

用户给出的 reference implementation 路径可访问：

```text
D:\PKU\OFEC\project\ofec-0.1.0
```

本轮没有复制 OFEC_CNN 代码。后续如果参考其参数、公式或实现逻辑，必须在 README 或代码注释中写明：“参考 OFEC_CNN 的参数/逻辑，本仓库重新实现”。

## 希望得到的 review 输出

请按严重程度列出问题：

- Critical：会违反用户 prompt、论文边界或导致后续实现方向错误的问题。
- Important：会影响可维护性、正确性验证或复现实验的问题。
- Minor：命名、文档清晰度、结构细节建议。

如果没有问题，请明确说明 skeleton 是否可以进入下一轮 backend 实现。
