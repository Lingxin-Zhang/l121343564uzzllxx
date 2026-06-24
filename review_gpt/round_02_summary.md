# Round 02 Summary: EventUpdateKernel Correctness

## 上一轮已实现内容

上一轮完成了最小 GF(2) backend correctness 闭环：

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `matrix_utils.py` 中的 GF(2) 输入规约和 shape 校验
- `tests/test_correctness.py` 中的 random input、density、block width、`apply` 和 `apply_many` correctness 测试

上一轮 pytest 结果为：

```text
27 passed
```

## 本轮修改文件

- `AGENTS.md`
- `README.md`
- `linear_kernel/event_update.py`
- `linear_kernel/packed_batch.py`
- `tests/test_correctness.py`
- `review_gpt/round_02_summary.md`
- `review_gpt/latest.md`

## 本轮功能说明

### `EventUpdateKernel`

实现了 event-driven GF(2) 输出更新：

```text
new_value = current_value XOR A[j, :] for j in flipped_positions
```

行为约束：

- `__init__` 保存 `matrix`、`n`、`r`
- `update(current_value, flipped_positions)` 返回新的 unpacked `np.uint8` bit vector
- `current_value` 必须是 shape `(r,)`
- `flipped_positions` 支持 list 或 `np.ndarray`
- `flipped_positions` 必须是一维且所有位置在 `[0, n)` 内
- 不修改输入 `current_value`，返回 copy

### `PackedBatchGF2Kernel`

仅统一接口名：

- 将 skeleton 方法 `apply_batch` 改为 `apply_many`
- 仍保持 `raise NotImplementedError`
- 本轮没有实现 packed backend

### 文档更新

- `AGENTS.md` 增加“每轮提交规范”
- `AGENTS.md` 同步 backend 当前状态
- `README.md` 同步当前状态：已实现 `NaiveGF2Kernel`、`SparseXorKernel`、`BlockLUTKernel`、`EventUpdateKernel` 和最小 correctness 测试；尚未实现 `PackedBatchGF2Kernel`、`HybridPlanner` 和 benchmark

## 测试结果

运行命令：

```bash
python -m pytest tests/test_correctness.py -q
```

结果：

```text
36 passed
```

## 已知问题

- `PackedBatchGF2Kernel` 尚未实现，仅保留 `apply_many` skeleton。
- `HybridPlanner` 尚未实现。
- 尚未实现 benchmark，也没有任何 speedup 数字或论文图。
- 工作树中存在与本轮无关的 `paper/draft` 本地变化，本轮未修改、未提交这些文件。

## 下一轮建议

下一轮建议先实现 `PackedBatchGF2Kernel` 的 unpacked correctness 版本或补充更系统的 validation tests；在 packed backend correctness 稳定前，不建议进入 benchmark。
