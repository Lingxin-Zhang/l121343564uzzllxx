# Round 07 Summary: PackedBlockLUT Correctness and Benchmarks

## Modified Files

- `AGENTS.md`
- `README.md`
- `linear_kernel/matrix_utils.py`
- `linear_kernel/packed_block_lut.py`
- `linear_kernel/__init__.py`
- `tests/test_correctness.py`
- `benchmarks/bench_block_width.py`
- `benchmarks/bench_density.py`
- `benchmarks/bench_batch.py`
- `scripts/plot_results.py`
- `review_gpt/latest.md`
- `review_gpt/round_07_summary.md`
- `results/raw/block_width.csv`
- `results/raw/density.csv`
- `results/raw/batch.csv`
- `results/figures/block_width_vs_latency.png`
- `results/figures/block_width_table_size.png`
- `results/figures/density_backend_comparison.png`
- `results/figures/batch_crossover.png`

## Implementation

- Implemented uint16 bit packing helpers with little-endian bit order:
  `bits[0]` maps to uint16 bit 0.
- Implemented `PackedBlockLUTKernel`.
- Added packed and unpacked correctness coverage.
- Added `PackedBlockLUT` to all existing benchmark scripts.
- Updated plots to include `PackedBlockLUT` and table-size comparison.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
85 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated CSV files in results/raw/
generated PNG figures in results/figures/
```

## Result Summary

- Packed tables are 8x smaller than unpacked `BlockLUT` tables for r=16.
- `PackedBlockLUT` is faster than unpacked `BlockLUT` in this run.
- `PackedBlockLUT` still does not beat the NumPy-based or sparse baselines in
  this Python implementation.
- Likely reasons: Python mask extraction, per-sample loops in `apply_many`,
  validation/unpack overhead, and small matrix/output sizes.

## Known Issues

- `HybridPlanner` is not implemented.
- `PackedBlockLUT.apply_many` is not vectorized.
- No speedup conclusions are claimed from this run.

## Next Step

Profile packed execution separately from unpacking, then decide whether to
vectorize batch mask extraction.
