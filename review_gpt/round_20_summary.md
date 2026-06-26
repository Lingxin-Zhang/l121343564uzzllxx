# Round 20 Summary

## Goal

Add and document a stricter long-stream cache-width diagnostic for L2/L3
`block_width` conclusions. The specific user requirement was that L3-related
support must come from 20x long-bitstream experiments and show a stable margin
of at least 20%.

## Modified Files

- `AGENTS.md`
- `README.md`
- `benchmarks/bench_long_stream_cache_width.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round09_results.py`
- `tests/test_long_stream_cache_width.py`
- `results/raw/long_stream_cache_width.csv`
- `results/summary/long_stream_cache_width_summary.csv`
- `results/figures/experiment_round09_long_stream_cache_width.png`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`
- `results/logs/round09_long_stream_cache_width.log`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_09_cache_width_summary.md`
- `review_gpt/round_20_summary.md`

## Changes

- Added a long-stream `PackedBlockLUTKernel` cache-width benchmark.
- Added summary fields for best L1/L2/L3 widths, latency ratios, CV stability,
  and `l2_strong_20x_claim` / `l3_strong_20x_claim`.
- Updated the Round 9 figure so L2/L1 and L3/L1 ratios are shown separately
  with a 0.8 gate for "20% faster".
- Added a regression test that requires 20x stream size, stable CV, and ratio
  `<= 0.8` before an L3 strong claim can become true.
- Documented in `AGENTS.md` and `README.md` that L2/L3 results below this gate
  are diagnostic only.

## Verification

Commands run:

```bash
python scripts/summarize_results.py
python scripts/plot_experiment_round09_results.py
python -m pytest tests/test_long_stream_cache_width.py tests/test_result_summary.py -q
python -m pytest -q
```

Result:

- `14 passed, 4 warnings`
- Full test suite: `293 passed, 1 skipped, 26 warnings`
- `results/raw/long_stream_cache_width.csv`: 24 rows, all
  `correctness_passed=True`
- `results/summary/long_stream_cache_width_summary.csv`: 4 rows, all
  `is_20x_long_stream=True`

## Result Status

- L2: no condition reaches the stable 20% gate.
- L3: one condition reaches the stable 20% gate:
  `ebch_256_239_r17`, `iterations=5`, `block_width=16`, ratio `0.797`.

## Known Issues

- The result is still a wall-clock Python diagnostic rather than a
  hardware-counter study.
- The eBCH-like profile is a candidate profile and remains labeled as such.
- Do not turn this into a universal L3 claim.

## Next Steps

- For stronger L2 evidence, run a targeted L2 boundary sweep with more repeats.
- For stronger L3 evidence, replicate the passing condition on another machine
  or add hardware-counter profiling.
