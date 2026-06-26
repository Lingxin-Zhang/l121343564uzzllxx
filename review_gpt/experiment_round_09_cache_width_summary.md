# Experiment Round 09 Cache-Width Summary

## Goal

Test whether larger `PackedBlockLUTKernel` block widths whose LUT footprints
fit L2 or L3 can beat the best L1-fitting width on long synthetic component
streams. The result is a cache-width diagnostic, not a BER result and not a
full-decoder result.

## Implementation

- Added `benchmarks/bench_long_stream_cache_width.py`.
- Added long-stream summary support in `scripts/summarize_results.py`.
- Added `scripts/plot_experiment_round09_results.py`.
- Added tests in `tests/test_long_stream_cache_width.py`.
- Documented the benchmark and claim gate in `README.md` and `AGENTS.md`.

## Claim Gate

L2/L3 cache-width claims are marked strong only when all are true:

1. the stream is a 20x long stream: `total_bits >= 1,342,177,280`;
2. correctness passes for all rows in the summary group;
3. the best L2 or L3 width has latency ratio `<= 0.8` versus the best L1
   width;
4. both the best L1 row and compared L2/L3 row have latency CV `<= 0.10`.

Rows failing any item are diagnostic observations only.

## Benchmark Run

Command:

```bash
python -m benchmarks.bench_long_stream_cache_width --preset paper --code-profiles bch_255_239_r16,ebch_256_239_r17 --total-bits 1342177280 --iterations 1,5 --block-widths 6,8,10,12,14,16 --repeats 5
```

Log:

- `results/logs/round09_long_stream_cache_width.log`

Generated:

- `results/raw/long_stream_cache_width.csv`
- `results/summary/long_stream_cache_width_summary.csv`
- `results/figures/experiment_round09_long_stream_cache_width.png`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`

## Result Audit

| Metric | Value |
|---|---:|
| Raw rows | 24 |
| Summary rows | 4 |
| Raw rows with `correctness_passed=True` | 24 |
| Summary rows with `is_20x_long_stream=True` | 4 |
| Summary rows with `l2_strong_20x_claim=True` | 0 |
| Summary rows with `l3_strong_20x_claim=True` | 1 |

## Per-Condition Summary

| Code profile | Iterations | Best L1 width | Best L1 latency us | Best L2 width | L2/L1 | L2 strong | Best L3 width | L3/L1 | L3 strong |
|---|---:|---:|---:|---:|---:|---|---:|---:|---|
| `bch_255_239_r16` | 1 | 8 | 1.004 | 14 | 0.895 | False | 16 | 0.972 | False |
| `bch_255_239_r16` | 5 | 8 | 1.026 | 14 | 0.898 | False | 16 | 0.951 | False |
| `ebch_256_239_r17` | 1 | 8 | 0.788 | 12 | 0.807 | False | 16 | 0.712 | False |
| `ebch_256_239_r17` | 5 | 8 | 0.702 | 12 | 0.937 | False | 16 | 0.797 | True |

## Interpretation for Review

- L2 is sometimes faster than L1, but the committed 20x long-stream data does
  not support a stable 20% L2 claim.
- L3 has one condition that passes the stricter gate:
  `ebch_256_239_r17`, `iterations=5`, `block_width=16`.
- The `ebch_256_239_r17`, `iterations=1` row is fast enough in ratio, but it is
  not marked strong because the L1 comparison is noisy.
- Any paper-facing statement must say "under the tested eBCH-like long-stream
  condition" rather than presenting L3 as universally better.

## Verification

Commands:

```bash
python scripts/summarize_results.py
python scripts/plot_experiment_round09_results.py
python -m pytest tests/test_long_stream_cache_width.py tests/test_result_summary.py -q
python -m pytest -q
```

Result:

- `14 passed, 4 warnings`
- Full test suite: `293 passed, 1 skipped, 26 warnings`

## Known Limits

- This benchmark uses Python/NumPy execution and wall-clock timing; it does not
  include hardware performance counters.
- The eBCH-like profile is still marked `candidate_unverified`.
- No full decoder, BER, or external-code implementation is involved.
