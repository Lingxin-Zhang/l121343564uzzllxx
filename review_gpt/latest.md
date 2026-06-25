# Latest Review Summary

Current round: Round 08 - Vectorized PackedBlockLUT Batch and Stream Benchmark

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
- `results/raw/block_width.csv`
- `results/raw/density.csv`
- `results/raw/batch.csv`
- `results/raw/stream.csv`
- `results/figures/block_width_vs_latency.png`
- `results/figures/block_width_table_size.png`
- `results/figures/density_backend_comparison.png`
- `results/figures/batch_crossover.png`
- `results/figures/stream_throughput.png`

## Implementation

- Vectorized `PackedBlockLUTKernel.apply_many_packed` so Python loops over LUT
  blocks, not over every batch row.
- Kept `apply_packed(x)` unchanged for single component-word execution.
- Added correctness coverage showing vectorized `apply_many_packed(X)` matches
  per-row `apply_packed(x)` for small and large batches.
- Added `PackedBlockLUT.apply_many_packed` to `bench_batch.py` so packed
  execution can be measured separately from unpacking.
- Added `benchmarks/bench_stream.py` for chunked M-level bit-stream benchmarks.
- Added stream plotting to `scripts/plot_results.py`.
- Updated run-all scripts to execute the stream benchmark.
- Added `AGENTS.local.md.example` and ignored local `AGENTS.local.md`.
- Documented generic benchmark terms and the current `r <= 16` packed-output
  limitation.

## Benchmark Terms

- `apply(x)`: process one component word, such as one 255-bit input vector.
- `apply_many(X)`: process a batch of component words, with
  `X.shape = (batch_size, n)`.
- `batch_size`: number of component words processed in one batch call.
- `total_bits`: total bit count in a synthetic bit stream.
- `num_words = total_bits // component_n`: number of component words cut from
  the bit stream.
- `chunk_words`: number of component words processed per chunk to avoid large
  one-shot memory allocations.

Example: `total_bits = 1,000,000` and `component_n = 255` gives
`num_words = 3921`, so `X.shape = (3921, 255)`.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
160 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated results/raw/block_width.csv
generated results/raw/density.csv
generated results/raw/batch.csv
generated results/raw/stream.csv
generated results/figures/block_width_vs_latency.png
generated results/figures/block_width_table_size.png
generated results/figures/density_backend_comparison.png
generated results/figures/batch_crossover.png
generated results/figures/stream_throughput.png
```

PDF figures were also generated locally, but remain ignored by git.

## Result Summary

- Vectorized `apply_many_packed` is implemented.
- Correctness passed for all current tests.
- Stream benchmark CSV and PNG were generated.
- In the batch benchmark, `PackedBlockLUT.apply_many_packed` is faster than
  `PackedBlockLUT.apply_many` for most larger batch settings because it avoids
  unpacking to a uint8 bit matrix. One large-batch point was close enough that
  the unpacked path measured slightly faster in this run.
- In the M-level stream benchmark, `PackedBlockLUT.apply_many_packed` was the
  fastest backend among the tested stream backends in this run.
- This is still a Python/NumPy micro-benchmark result, not a paper conclusion.

## Known Issues

- `HybridPlanner` is not implemented.
- `PackedBlockLUTKernel` only supports output width `r <= 16`.
- Mask extraction is still a likely bottleneck.
- NumPy batch matrix multiply remains a strong baseline.
- Current matrix/output sizes are small.
- A true larger-output packed implementation would need `uint32`/`uint64` or
  multi-word packing.

## Next Step

Possible next steps:

1. Profile `apply_many_packed` to separate mask extraction from LUT XOR.
2. Add `uint32`/`uint64` or multi-word packed output support.
3. Test a real component-kernel or event-update workload after keeping the
   public code generic and reimplemented.
