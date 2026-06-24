# 论文故事

高速光通信 FEC 中，product-like、staircase 和 oFEC 等结构会反复调用 BCH/eBCH component code。许多热点操作，例如 syndrome computation、parity generation 和少量 bit flip 后的 syndrome update，都可以抽象为固定矩阵上的 GF(2) 线性内核。

单一 backend 不一定适合所有 workload。稀疏输入、批量输入、block width、cache 行为和 event update 频率都会影响最佳执行方式。因此，本项目的故事是 exact workload-aware hybrid backend：在不改变编码定义、译码决策和 BER 的前提下降低 runtime。
