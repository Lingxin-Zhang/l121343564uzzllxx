# Round 22 Summary

## Goal

Perform Round 10.5 long-stream cache-width schema / semantics cleanup. The
round fixes the stream-size field names and migrates existing CSVs. It does not
rerun large experiments.

## Modified Files

- `benchmarks/bench_long_stream_cache_width.py`
- `scripts/migrate_long_stream_cache_width_schema.py`
- `scripts/summarize_results.py`
- `tests/test_long_stream_cache_width.py`
- `tests/test_result_summary.py`
- `results/raw/long_stream_cache_width.csv`
- `results/raw/long_stream_cache_width_replication.csv`
- `results/summary/long_stream_cache_width_summary.csv`
- `results/summary/long_stream_cache_width_replication_summary.csv`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_10_5_long_stream_schema_cleanup.md`
- `review_gpt/round_22_summary.md`

## Changes

- Added `stream_input_bits` to long-stream raw and summary schemas.
- Corrected `stream_input_bytes` to store true bytes:
  `ceil(stream_input_bits / 8)`.
- Added a migration script for existing long-stream raw CSVs.
- Added tests for raw rows, CLI output, summary rows, replication summary, and
  plot compatibility.
- Regenerated summaries and the Round 9 diagnostic figure.

## Verification

Commands:

```bash
python scripts/migrate_long_stream_cache_width_schema.py
python scripts/summarize_results.py
python scripts/plot_experiment_round09_results.py
python -m pytest tests/test_long_stream_cache_width.py tests/test_result_summary.py -q
python -m pytest -q
```

Results:

- Targeted tests: `16 passed, 5 warnings`
- Full test suite: `295 passed, 1 skipped, 27 warnings`

## Audit

- `long_stream_cache_width.csv`: 24 rows, migrated schema.
- `long_stream_cache_width_replication.csv`: 12 rows, migrated schema.
- Summary CSVs now include `stream_input_bits` and true `stream_input_bytes`.
- Measurement values were not changed except for the corrected stream-size
  schema.

## Known Issues

- This round does not change L2/L3 performance interpretation.
- L2 evidence remains mixed.
- L3 remains an eBCH-like long-stream conditional result only.
