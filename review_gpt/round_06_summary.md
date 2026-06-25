# Round 06 Summary: Benchmark Result Check and Figure Updates

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

## Implementation

- Allowed benchmark CSV files and PNG figures to be tracked.
- Kept PDF figures and local sensitive directories ignored.
- Reworked the block-width plot to show latency and table size together.
- Changed `Naive` and `SparseXor` in the block-width plot into horizontal latency
  baselines.
- Moved density and batch legends outside the plot area.
- Re-ran pytest and the full benchmark pipeline.

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

## Result Summary

- The block-width run showed `SparseXor` as fastest in this measurement.
- `BlockLUT` latency decreased with larger `block_width`, but table memory grew
  quickly.
- The density run showed `Naive` and `PackedBatch` close to each other; `SparseXor`
  slowed as density increased.
- The batch run also showed `Naive.apply_many` and `PackedBatch.apply_many` close
  to each other.
- Current measurements include Python-loop and validation overhead.

## Known Issues

- `HybridPlanner` is not implemented.
- `PackedBatchGF2Kernel` is not a true packed-bit backend yet.
- `BlockLUT.apply_many` still uses per-sample Python loops.

## Next Step

Keep the current CSV/PNG files available for review, then decide whether to
separate validation overhead or vectorize `BlockLUT.apply_many` in a later round.
