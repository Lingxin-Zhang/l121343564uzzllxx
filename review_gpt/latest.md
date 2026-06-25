# Latest Review Summary

Current round: Round 07 - PackedBlockLUT Correctness and Benchmarks

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

- Added `pack_bits_to_uint16`, `unpack_uint16_to_bits`, and
  `pack_batch_bits_to_uint16`.
- Added `PackedBlockLUTKernel` with packed `np.uint16` LUT entries.
- Added `apply_packed`, `apply`, `apply_many_packed`, and `apply_many`.
- Exported `PackedBlockLUTKernel` from `linear_kernel`.
- Added correctness tests for pack/unpack helpers and packed BlockLUT outputs.
- Added `PackedBlockLUT` to block-width, density, and batch benchmarks.
- Added a separate `block_width_table_size` figure for table memory comparison.
- Updated public status docs and repaired the `AGENTS.md` workflow text.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
85 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated results/raw/block_width.csv
generated results/raw/density.csv
generated results/raw/batch.csv
generated results/figures/block_width_vs_latency.png
generated results/figures/block_width_table_size.png
generated results/figures/density_backend_comparison.png
generated results/figures/batch_crossover.png
```

PDF figures were also generated locally, but remain ignored by git.

## Result Summary

- `PackedBlockLUT` correctness passed against `Naive` for `apply`,
  `apply_many`, `apply_packed`, and `apply_many_packed`.
- `PackedBlockLUT` table size was 8x smaller than the original unpacked
  `BlockLUT` table in this r=16 setup.
- In the block-width benchmark, `PackedBlockLUT` was faster than unpacked
  `BlockLUT`, especially at larger block widths.
- `PackedBlockLUT` did not beat `Naive`, `PackedBatch`, or `SparseXor` in this
  run. The benchmark still includes Python mask extraction, per-sample
  `apply_many` loops, validation, and unpacking overhead.
- Current `PackedBatch` is still a correctness-first NumPy implementation, not a
  true packed-bit backend.

## Known Issues

- `HybridPlanner` is not implemented.
- `PackedBlockLUT.apply_many` still loops over samples in Python.
- `PackedBlockLUT.apply` unpacks back to uint8 bits for fair API comparison.
- The matrix/output sizes are small, so NumPy overhead can dominate some runs.

## Next Step

Possible next improvements:

1. Add a benchmark mode for `apply_packed` / `apply_many_packed` to isolate pure
   packed LUT execution from unpacking.
2. Vectorize packed mask extraction for batch inputs.
3. Consider Numba/Cython/C++ only after the Python-level profile is clear.
