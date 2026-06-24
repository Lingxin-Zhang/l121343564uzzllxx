# Latest Review Summary

当前最新轮次：Round 02 - EventUpdateKernel Correctness

## 上一轮已实现内容

上一轮完成：

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- GF(2) matrix/vector/batch validation helpers
- 最小 correctness 测试

上一轮 pytest 结果：

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

实现 `EventUpdateKernel.update(current_value, flipped_positions)`：

- 使用 `current_value XOR A[j, :]` 更新翻转位置贡献
- 支持 list 或 `np.ndarray` flipped positions
- 校验 `current_value` shape 为 `(r,)`
- 校验 flipped positions 为一维并在 `[0, n)` 内
- 返回新的 unpacked `np.uint8` bit vector，不修改输入 `current_value`

同步将 `PackedBatchGF2Kernel` skeleton 接口从 `apply_batch` 改为 `apply_many`，但没有实现 packed backend。

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

- `PackedBatchGF2Kernel` 尚未实现。
- `HybridPlanner` 尚未实现。
- benchmark 尚未实现，本轮未生成 speedup 数字或论文图。
- 本地存在与本轮无关的 `paper/draft` 变化，未纳入本轮提交。

## 下一步建议

优先实现 `PackedBatchGF2Kernel` 的 correctness-first 版本，并继续保持每轮更新 `review_gpt/latest.md` 与对应 `round_xx_summary.md`。
