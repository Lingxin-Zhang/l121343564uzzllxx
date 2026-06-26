# Experiment Round 10 Cache-Width Replication Summary

## Goal

Replicate the 20x long-stream cache-width diagnostic without overwriting the
main Round 9 CSV. The replication focuses on `iterations=5`, where the previous
main result showed the only strong L3 condition.

## Code Changes

- `benchmarks/bench_long_stream_cache_width.py`
  - Added `--output` so targeted replication runs can write to a separate CSV.
- `scripts/summarize_results.py`
  - Added `long_stream_cache_width_replication.csv` support.
  - Writes `results/summary/long_stream_cache_width_replication_summary.csv`.
- `tests/test_long_stream_cache_width.py`
  - Added a CLI test for custom output paths.

## Replication Command

```bash
python -m benchmarks.bench_long_stream_cache_width --preset paper --code-profiles bch_255_239_r16,ebch_256_239_r17 --total-bits 1342177280 --iterations 5 --block-widths 8,10,12,14,16,18 --repeats 7 --output results/raw/long_stream_cache_width_replication.csv
```

Log:

- `results/logs/round10_long_stream_cache_width_replication.log`

Runtime:

- `1425` seconds, about `23.75` minutes.

## Outputs

- `results/raw/long_stream_cache_width_replication.csv`
- `results/summary/long_stream_cache_width_replication_summary.csv`
- `results/logs/round10_long_stream_cache_width_replication.log`

## Audit

| Artifact | Rows | Correctness |
|---|---:|---|
| `long_stream_cache_width_replication.csv` | 12 | 12/12 true |
| `long_stream_cache_width_replication_summary.csv` | 2 | 2/2 true |

All summary rows are 20x long-stream rows.

## Results

| Code profile | Best L1 width | Best L1 latency us | Best L2 width | L2/L1 | L2 strong | Best L3 width | L3/L1 | L3 strong |
|---|---:|---:|---:|---:|---|---:|---:|---|
| `bch_255_239_r16` | 8 | 0.507 | 10 | 1.091 | False | 18 | 1.422 | False |
| `ebch_256_239_r17` | 8 | 0.716 | 12 | 0.697 | True | 14 | 0.649 | True |

## Interpretation

- The BCH `r=16` profile did not benefit from L2 or L3 widths in this
  replication.
- The eBCH-like `r=17` profile did benefit from both L2 and L3 widths in this
  replication.
- L3 is now supported by both the main Round 9 CSV and this replication, but
  the best L3 block width differs across runs (`16` in the main CSV,
  `14` in replication).
- L2 is not yet stable enough for strong wording because the main CSV did not
  mark L2 strong for the same eBCH-like condition.

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

## Claim Safety

Allowed wording:

- A condition-specific statement that the eBCH-like long-stream workload shows
  L3-fitting LUT widths can beat the best L1-fitting width by at least 20% under
  the current strict gate.
- A weaker statement that L2 shows a promising eBCH-like regime in the
  replication but needs another repeat before being used as a stable claim.

Forbidden wording:

- Do not say L2 is generally better than L1.
- Do not say L3 is generally better than L1.
- Do not claim full decoder or BER evidence.
- Do not claim hardware-counter evidence.
