# 创新边界

partitioned LUT encoder、BCH table lookup、CRC slicing 和 M4RI/Four Russians 都是已有或相邻工作。因此，本项目不能把 block-LUT encoder 本身作为主创新，也不能声称首次提出线性码 block-LUT 编码器。

本项目的区别应聚焦在 optical FEC repeated kernel workload、多个 bit-exact backend 的 hybrid selection、cache/workload-aware execution，以及端到端 component-loop runtime evaluation。论文表述必须强调 runtime reduction without changing decoding decisions。
