# Review Handoff: Minimal Correctness Backends

## 用户本轮要求

本轮只实现最小 correctness 闭环，不跑大规模 benchmark，不生成论文图，不改论文故事。

需要实现并测试三个 backend：

1. `NaiveGF2Kernel`
2. `SparseXorKernel`
3. `BlockLUTKernel`

统一接口：

```python
apply(x)       # x shape = (n,)
apply_many(X)  # X shape = (batch, n)
```

输出必须是 unpacked bit vector，dtype 为 `np.uint8`，值只能是 0/1。

## 本轮修改文件

- `linear_kernel/matrix_utils.py`
- `linear_kernel/naive.py`
- `linear_kernel/sparse_xor.py`
- `linear_kernel/block_lut.py`
- `tests/test_correctness.py`
- `review_gpt/README.md`
- `review_gpt/2026-06-24-correctness-backends.md`

## 实现摘要

### `matrix_utils.py`

新增/补充：

- `as_gf2_array`
- `require_gf2_matrix`
- `require_gf2_vector`
- `require_gf2_batch`

这些 helper 会将输入规约为 unpacked `np.uint8` GF(2) 数组，并检查 vector/batch 的输入长度是否匹配矩阵的 `n`。

### `NaiveGF2Kernel`

实现：

```python
f(x) = x @ A mod 2
```

支持 `apply(x)` 和 `apply_many(X)`，输出 shape 分别为 `(r,)` 和 `(batch, r)`。

### `SparseXorKernel`

按用户要求统一命名：

```python
position_contribution[j] = A[j, :]
```

对输入中 `x[j] == 1` 的位置做 XOR。空 active set 返回全零输出。

### `BlockLUTKernel`

按 `block_width` 切分输入位置，对每个块预计算：

```python
T_b[mask] = 该块局部 mask 对输出的 XOR contribution
```

在线阶段从每个块取 `mask_b` 并 XOR `T_b[mask_b]`。支持最后一个不足 `block_width` 的短块。

## 测试覆盖

`tests/test_correctness.py` 覆盖：

- 随机矩阵 `A`，`n=255, r=16`
- 每个 density 生成 1000 个随机输入
- density: `0.01`, `0.05`, `0.5`
- block width: `4`, `8`, `12`, `16`, `20`
- `apply`
- `apply_many`
- backend 输出 shape、dtype、0/1 值检查
- 输入 vector/batch 宽度不匹配时抛 `ValueError`

## 已验证命令

```bash
python -m pytest tests/test_correctness.py -q
```

输出：

```text
27 passed in 8.77s
```

## 本轮刻意未做

- 未实现 `PackedBatchGF2Kernel`
- 未实现 `EventUpdateKernel`
- 未实现 `HybridPlanner`
- 未跑 benchmark
- 未生成 speedup 数字
- 未生成论文图
- 未修改 paper story / novelty boundary

## 请 review GPT 重点检查

1. 三个 backend 的输出是否始终为 unpacked `np.uint8` 0/1 bit vector。
2. `SparseXorKernel` 是否正确使用 `position_contribution` 命名和语义。
3. `BlockLUTKernel` 的 mask 位序、短块处理和 LUT 构造是否正确。
4. `apply_many` 当前使用逐行调用是否符合“最小 correctness 闭环”的范围。
5. 测试是否覆盖了用户要求的 density、block width、single input 和 batch input。
6. 是否有任何地方暗示了 benchmark、speedup 或 BER 改善。
