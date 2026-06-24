# 方法推导笔记

本项目的核心抽象是固定 GF(2) 线性内核：

```text
f(x) = xA
```

其中 `A` 是固定二元矩阵，`x` 是输入 bit 向量。block-LUT backend 可以把输入切成若干 block，并预先为每个 block 建表：

```text
f(x) = xor_b T_b[x_b]
```

后续会补充 sparse-column XOR、packed batch GF(2) execution 和 event-driven syndrome update 的推导，并说明它们都必须与 baseline 输出 bit-exact 一致。
