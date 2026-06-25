# Latest Review Summary

Current round: Round 06 - Benchmark Result Check and Figure Updates

## Modified Files

- `.gitignore`
- `scripts/plot_results.py`
- `review_gpt/latest.md`
- `review_gpt/round_06_summary.md`
- `results/raw/block_width.csv`
- `results/raw/density.csv`
- `results/raw/batch.csv`
- `results/figures/block_width_vs_latency.png`
- `results/figures/density_backend_comparison.png`
- `results/figures/batch_crossover.png`

## Simple Terms

- `block_width`: how many input bits a `BlockLUT` table lookup consumes at once.
- `density`: the fraction of 1s in an input vector.
- `batch_size`: how many input vectors are processed in one call.
- `latency_per_word_us`: average microseconds needed to process one input vector.
- `table_size_bytes`: memory used by `BlockLUT` lookup tables.

## Implementation

- Allowed `results/raw/*.csv` and `results/figures/*.png` to be tracked.
- Kept `results/figures/*.pdf`, `paper/`, and `references/` ignored.
- Updated the block-width figure to use:
  - `block_width` on the x-axis,
  - latency on the left y-axis,
  - `BlockLUT` table size on the right y-axis,
  - horizontal `Naive` and `SparseXor` latency baselines,
  - a `BlockLUT` latency curve and a table-size curve.
- Moved density and batch legends outside the plotting area.
- Kept all figure titles generic to GF(2) benchmarks.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
49 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated results/raw/block_width.csv
generated results/raw/density.csv
generated results/raw/batch.csv
generated results/figures/block_width_vs_latency.png
generated results/figures/density_backend_comparison.png
generated results/figures/batch_crossover.png
```

PDF figures were also generated locally, but remain ignored by git.

## Result Summary

- All three CSV files were generated.
- All three PNG figures were generated and are now tracked for review.
- In the block-width run, `SparseXor` was the fastest backend across the tested
  `block_width` values. `BlockLUT` latency decreased as `block_width` increased,
  while table size grew quickly.
- In the density run, `Naive` and `PackedBatch` were very close and alternated
  as fastest in this run. `SparseXor` became slower as density increased.
- In the batch run, `Naive.apply_many` and `PackedBatch.apply_many` were close
  and alternated as fastest depending on batch size.
- These results are reasonable for the current implementation, but they should
  not be interpreted as optimized backend conclusions.

## Known Issues

- `HybridPlanner` is not implemented.
- `PackedBatchGF2Kernel` is still a correctness-first NumPy implementation, not
  a true packed-bit backend.
- `BlockLUT.apply_many` still loops over samples in Python.
- Validation and Python-loop overhead are included in the measured latency.
- The matrix/output sizes are small, so NumPy overhead can dominate some runs.

## Next Step

Possible next improvements:

1. Add benchmark options to separate validation overhead from kernel execution.
2. Vectorize `BlockLUT.apply_many` before drawing stronger performance claims.
3. Add repeated machine/environment metadata to benchmark CSVs.
