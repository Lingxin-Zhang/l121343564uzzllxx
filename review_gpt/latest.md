# Latest Review Summary

Current round: Round 9 long-stream cache-width diagnostic cleanup.

## Goal

Add a reproducible long-stream diagnostic for `PackedBlockLUTKernel`
`block_width` choices and tighten the claim gate for L2/L3 cache-width
conclusions. This round is code/result-review focused only: no BER, no full
decoder, no new algorithmic backend, and no paper conclusion was added.

## Skills Used

- `results-analysis`: used to audit raw/summary CSV row counts, correctness
  flags, latency ratios, and strong-claim gates.
- `superpowers:verification-before-completion`: used before reporting the
  verification state.

## Modified Files

- `benchmarks/bench_long_stream_cache_width.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round09_results.py`
- `tests/test_long_stream_cache_width.py`
- `README.md`
- `AGENTS.md`
- `results/raw/long_stream_cache_width.csv`
- `results/summary/long_stream_cache_width_summary.csv`
- `results/figures/experiment_round09_long_stream_cache_width.png`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`
- `results/logs/round09_long_stream_cache_width.log`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_09_cache_width_summary.md`
- `review_gpt/round_20_summary.md`

## Benchmark Command

The committed long-stream result was generated with:

```bash
python -m benchmarks.bench_long_stream_cache_width --preset paper --code-profiles bch_255_239_r16,ebch_256_239_r17 --total-bits 1342177280 --iterations 1,5 --block-widths 6,8,10,12,14,16 --repeats 5
```

Log: `results/logs/round09_long_stream_cache_width.log`

This is a 20x long-bitstream diagnostic relative to the earlier
`67,108,864`-bit stream scale. It processes approximately `1.342G` input bits
per condition before iteration multiplication.

## Result Summary

Raw CSV:

- `results/raw/long_stream_cache_width.csv`
- Rows: 24
- `correctness_passed=True`: 24/24

Summary CSV:

- `results/summary/long_stream_cache_width_summary.csv`
- Rows: 4
- `is_20x_long_stream=True`: 4/4
- `l2_strong_20x_claim=True`: 0/4
- `l3_strong_20x_claim=True`: 1/4

Strong L2/L3 gate used by the summary:

1. `total_bits >= 1,342,177,280`;
2. compared result has `correctness_all_true=True`;
3. best L2 or L3 latency ratio versus best L1 latency is `<= 0.8`;
4. both compared latency CV values are `<= 0.10`.

## Key Observations

| Code profile | Iterations | Best L1 width | Best L2 ratio vs L1 | L2 strong 20x | Best L3 ratio vs L1 | L3 strong 20x |
|---|---:|---:|---:|---|---:|---|
| `bch_255_239_r16` | 1 | 8 | 0.895 | False | 0.972 | False |
| `bch_255_239_r16` | 5 | 8 | 0.898 | False | 0.951 | False |
| `ebch_256_239_r17` | 1 | 8 | 0.807 | False | 0.712 | False |
| `ebch_256_239_r17` | 5 | 8 | 0.937 | False | 0.797 | True |

Interpretation for review:

- L2 widths often beat the best L1 width, but none reached the requested
  stable 20% gap in the 20x long-stream run.
- L3 has one supported condition under this gate:
  `ebch_256_239_r17`, `iterations=5`, `block_width=16`, ratio `0.797`.
- The `ebch_256_239_r17`, `iterations=1` L3 row is faster by more than 20%,
  but it is not marked strong because the best L1 comparison CV is high.
- Therefore any L3-related paper wording must be condition-specific, not
  universal.

## Figure Status

Regenerated:

- `results/figures/experiment_round09_long_stream_cache_width.png`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`

The right panel now separates L2/L1 and L3/L1 ratios and shows the 0.8 gate,
instead of merging L2 and L3 into one bar.

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
- CSV audit confirmed 24/24 raw rows have `correctness_passed=True`.

## Known Issues / Limits

- This is still a Python microbenchmark, so cache behavior is diagnostic rather
  than a hardware-counter proof.
- No L2 condition currently satisfies the requested stable 20% gate.
- The only L3 strong condition is for the candidate eBCH-like `r=17` profile at
  `iterations=5`; do not generalize it to every code profile or every workload.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains unrelated and
  untracked.

## Next Steps

- If stronger L2 evidence is needed, run a targeted L2-only sweep with
  additional widths around the L2 footprint boundary and larger repeat counts.
- If stronger L3 evidence is needed, repeat the one passing eBCH condition on a
  second machine or with hardware-counter profiling.
- Keep all L2/L3 wording tied to `long_stream_cache_width_summary.csv`.
