# Latest Review Summary

Current round: Round 10 long-stream cache-width replication.

## Goal

Add a non-overwriting replication path for the long-stream cache-width
diagnostic and run a heavier 20x validation sweep for L2/L3 `block_width`
behavior. This round is code/result-review focused only: no BER, no full
decoder, no new algorithmic backend, and no paper conclusion was added.

## Skills Used

- `research-experiment-driver`: used to keep the replication focused on the
  cache-width claim gate instead of broad full-sweep benchmarking.
- `results-analysis`: used to audit raw/summary CSV row counts, correctness
  flags, latency ratios, and strong-claim gates.
- `superpowers:verification-before-completion`: used before reporting the
  verification state.

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

## Replication Benchmark Command

```bash
python -m benchmarks.bench_long_stream_cache_width --preset paper --code-profiles bch_255_239_r16,ebch_256_239_r17 --total-bits 1342177280 --iterations 5 --block-widths 8,10,12,14,16,18 --repeats 7 --output results/raw/long_stream_cache_width_replication.csv
```

Log: `results/logs/round10_long_stream_cache_width_replication.log`

Runtime was about `1425` seconds (`23.75` minutes), so the heavier 20x
replication stayed under the requested one-hour-per-run budget.

This is a 20x long-bitstream diagnostic relative to the earlier
`67,108,864`-bit stream scale. It processes approximately `1.342G` input bits
per condition before iteration multiplication.

## Result Summary

Raw CSV:

- `results/raw/long_stream_cache_width_replication.csv`
- Rows: 12
- `correctness_passed=True`: 12/12

Summary CSV:

- `results/summary/long_stream_cache_width_replication_summary.csv`
- Rows: 2
- `is_20x_long_stream=True`: 2/2
- `l2_strong_20x_claim=True`: 1/2
- `l3_strong_20x_claim=True`: 1/2

Strong L2/L3 gate used by the summary:

1. `total_bits >= 1,342,177,280`;
2. compared result has `correctness_all_true=True`;
3. best L2 or L3 latency ratio versus best L1 latency is `<= 0.8`;
4. both compared latency CV values are `<= 0.10`.

## Replication Observations

| Code profile | Iterations | Best L1 width | Best L2 ratio vs L1 | L2 strong 20x | Best L3 ratio vs L1 | L3 strong 20x |
|---|---:|---:|---:|---|---:|---|
| `bch_255_239_r16` | 5 | 8 | 1.091 | False | 1.422 | False |
| `ebch_256_239_r17` | 5 | 8 | 0.697 | True | 0.649 | True |

Interpretation for review:

- For `bch_255_239_r16`, L1 remained best in the replication; neither L2 nor L3
  should be claimed as better for this condition.
- For `ebch_256_239_r17`, both L2 width 12 and L3 width 14 passed the strict
  20x stable 20% gate in this replication.
- Compared with the previous main CSV, L3 strength is the more robust
  observation: both runs support an eBCH-like L3 advantage under `iterations=5`,
  although the best L3 width changed from 16 to 14.
- L2 strength is promising but less stable across runs: the previous main CSV
  did not mark L2 strong for the same eBCH-like condition, while this
  replication did.
- Therefore L3 can be discussed as condition-specific evidence; L2 should be
  described as a candidate regime that needs one more targeted repeat or
  hardware-counter validation before strong wording.

## Figure Status

No new figure was added for the replication. The existing Round 9 figure still
uses the main CSV; the replication CSV is a review/audit artifact.

## Verification

Commands run:

```bash
python scripts/summarize_results.py
python -m pytest tests/test_long_stream_cache_width.py tests/test_result_summary.py -q
python -m pytest -q
```

Result:

- `15 passed, 5 warnings`
- Full test suite: `294 passed, 1 skipped, 27 warnings`
- CSV audit confirmed 12/12 replication raw rows have
  `correctness_passed=True`.

## Known Issues / Limits

- This is still a Python microbenchmark, so cache behavior is diagnostic rather
  than a hardware-counter proof.
- L2 evidence is mixed across the main and replication CSVs; do not present it
  as a stable claim yet.
- L3 evidence is condition-specific to the candidate eBCH-like `r=17` profile at
  `iterations=5`; do not generalize it to every code profile or every workload.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains unrelated and
  untracked.

## Next Steps

- If stronger L2 evidence is needed, run one more L2-only repeat around widths
  10 and 12 for `ebch_256_239_r17`.
- If stronger L3 evidence is needed, repeat widths 14 and 16 on a second
  machine or with hardware-counter profiling.
- Keep all L2/L3 wording tied to `long_stream_cache_width_summary.csv` and
  `long_stream_cache_width_replication_summary.csv`.
