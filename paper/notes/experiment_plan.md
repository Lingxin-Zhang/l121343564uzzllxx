# 实验计划

后续实验首先评估 block width 对 latency 和 memory 的影响，观察查表规模、cache 行为和端到端 runtime 的折中。然后改变 input density，比较 naive、sparse XOR、block-LUT 和 packed batch 等 backend 的适用范围。

第二组实验关注 batch size crossover、event update speedup 和 repeated component syndrome loop speedup。每个实验都必须包含 correctness / bit-exact check，不得在未验证输出一致的情况下报告 speedup。

所有 benchmark 需要固定 random seed，包含 warmup 和多次重复，输出 mean/std，并保存 CSV 与论文图。
