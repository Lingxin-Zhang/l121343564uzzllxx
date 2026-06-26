# Latest Review Summary

Current round: Round 10.5 long-stream cache-width schema / semantics cleanup.

## Goal

Clean up the `long_stream_cache_width` raw/summary schema so input stream size
is represented with explicit and correct fields:

- `stream_input_bits`
- `stream_input_bytes`

This round only changes schema semantics and tests. It does not rerun 20x
long-stream benchmarks, does not run a broad full sweep, does not add
`BCH(511,484,r27)`, and does not add BER/full decoder/full OFEC work.

## Skills Used

- `results-analysis`: used to audit CSV schema, row counts, and unchanged
  measurement fields.
- `superpowers:test-driven-development`: used to add failing tests before the
  schema implementation.
- `superpowers:verification-before-completion`: used before reporting final
  verification status.

No subagent was used; the work was small and tightly coupled.

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

## What Changed

Previous issue:

- `stream_input_bytes` actually stored `num_words * component_n`, which is a
  bit count, not a byte count.

Current schema:

- `stream_input_bits = num_words * component_n`
- `stream_input_bytes = ceil(stream_input_bits / 8)`

Migration:

- Ran `python scripts/migrate_long_stream_cache_width_schema.py`.
- Existing raw CSVs were migrated by treating old `stream_input_bytes` values
  as legacy bit counts.
- No latency, throughput, CV, correctness, block-width, or LUT-size values were
  changed.

## Artifact Audit

| Artifact | Rows | Schema status |
|---|---:|---|
| `results/raw/long_stream_cache_width.csv` | 24 | has bits and true bytes |
| `results/raw/long_stream_cache_width_replication.csv` | 12 | has bits and true bytes |
| `results/summary/long_stream_cache_width_summary.csv` | 4 | has bits and true bytes |
| `results/summary/long_stream_cache_width_replication_summary.csv` | 2 | has bits and true bytes |

Audit result:

- Old raw rows and migrated raw rows have the same row counts.
- All old measurement fields except the corrected stream-size schema matched
  exactly.
- Example migrated value: old legacy `1342177200` bit count is now
  `stream_input_bits=1342177200` and `stream_input_bytes=167772150`.

## Result Semantics

The Round 9 / Round 10 latency conclusions did not change.

- L2 evidence remains mixed and should not be written as a stable strong claim.
- L3 evidence remains condition-specific to the eBCH-like long-stream workload.
- No final paper claim was added in this round.

## Commands Run

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

## Known Notes

- `scripts/summarize_results.py` still accepts legacy long-stream rows where
  only the old misnamed `stream_input_bytes` exists, but the committed raw and
  summary CSVs now use the new explicit schema.
- `results/figures/experiment_round09_long_stream_cache_width.pdf` was
  regenerated after the summary update; the plotting script did not require
  logic changes.
- Unrelated untracked review notes remain uncommitted:
  `review_gpt/round08_experiment_closeout_discussion.md` and
  `review_gpt/round_18_skill_and_figure_redesign_plan.md`.
