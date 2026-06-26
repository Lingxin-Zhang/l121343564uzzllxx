# Round 21 Summary

## Goal

Continue the cache-width exploration by adding a separate replication output
path and running a heavier 20x long-stream validation sweep under the one-hour
per-run budget.

## Modified Files

- `benchmarks/bench_long_stream_cache_width.py`
- `scripts/summarize_results.py`
- `tests/test_long_stream_cache_width.py`
- `results/raw/long_stream_cache_width_replication.csv`
- `results/summary/long_stream_cache_width_replication_summary.csv`
- `results/logs/round10_long_stream_cache_width_replication.log`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_10_cache_width_replication_summary.md`
- `review_gpt/round_21_summary.md`

## Changes

- Added `--output` to the long-stream cache-width benchmark.
- Added standalone replication summary generation for
  `long_stream_cache_width_replication.csv`.
- Added a regression test for custom benchmark output paths.
- Ran a 20x long-stream replication with `repeats=7`.

## Benchmark

```bash
python -m benchmarks.bench_long_stream_cache_width --preset paper --code-profiles bch_255_239_r16,ebch_256_239_r17 --total-bits 1342177280 --iterations 5 --block-widths 8,10,12,14,16,18 --repeats 7 --output results/raw/long_stream_cache_width_replication.csv
```

Runtime:

- `1425` seconds, about `23.75` minutes.

## Results

- Raw replication rows: 12
- Correctness: 12/12 true
- Summary rows: 2
- 20x long-stream rows: 2/2
- `l2_strong_20x_claim=True`: 1/2
- `l3_strong_20x_claim=True`: 1/2

The eBCH-like `r=17` profile passed the strict L2 and L3 gates in this
replication. BCH `r=16` did not.

## Verification

Commands:

```bash
python scripts/summarize_results.py
python -m pytest tests/test_long_stream_cache_width.py tests/test_result_summary.py -q
python -m pytest -q
```

Result:

- `15 passed, 5 warnings`
- Full test suite: `294 passed, 1 skipped, 27 warnings`

## Known Issues

- L2 evidence is mixed across the main and replication CSVs.
- L3 evidence is condition-specific to the eBCH-like profile and should not be
  generalized.
- No hardware counters were collected.

## Next Steps

- One more L2-focused repeat could decide whether the eBCH-like L2 advantage is
  stable.
- A second-machine run or hardware-counter check would strengthen the L3 cache
  interpretation.
