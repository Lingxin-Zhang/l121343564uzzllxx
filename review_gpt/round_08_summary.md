# Round 08 Summary: Vectorized PackedBlockLUT Batch and Stream Benchmark

## Modified Files

- `.gitignore`
- `AGENTS.md`
- `AGENTS.local.md.example`
- `README.md`
- `linear_kernel/packed_block_lut.py`
- `tests/test_correctness.py`
- `benchmarks/bench_batch.py`
- `benchmarks/bench_stream.py`
- `scripts/plot_results.py`
- `scripts/run_all_benchmarks.py`
- `review_gpt/latest.md`
- `review_gpt/round_08_summary.md`
- benchmark CSV files under `results/raw/`
- benchmark PNG figures under `results/figures/`

## Implementation

- Replaced per-row Python looping in `PackedBlockLUTKernel.apply_many_packed`
  with block-wise vectorized mask extraction and table lookup.
- Added stream benchmark for chunked synthetic bit streams.
- Added `PackedBlockLUT.apply_many_packed` to batch benchmarking.
- Added stream throughput plotting.
- Added local reference path example and ignored the real local override file.
- Updated public docs with benchmark term definitions.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
160 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated block_width.csv, density.csv, batch.csv, stream.csv
generated block_width_vs_latency.png, block_width_table_size.png,
density_backend_comparison.png, batch_crossover.png, stream_throughput.png
```

## Result Summary

- Vectorized `apply_many_packed` is implemented and correctness-tested.
- `PackedBlockLUT.apply_many_packed` is faster than unpacking through
  `PackedBlockLUT.apply_many` for most larger batch settings in this run.
- In the stream benchmark, `PackedBlockLUT.apply_many_packed` was the fastest
  tested stream backend.
- No speedup or paper conclusion is claimed.

## Known Issues

- `HybridPlanner` is not implemented.
- Packed output is limited to `r <= 16`.
- Further gains may require profiling, wider packed output support, or compiled
  inner loops.

## Next Step

Profile the vectorized packed path before changing algorithms further.
