# Experiment Round 10.5 Long-Stream Schema Cleanup

## Goal

Fix the schema semantics of the long-stream cache-width artifacts. This round
does not rerun large 20x experiments; it only migrates existing CSVs and updates
code/tests so future rows use explicit bit and byte fields.

## Problem

The old raw CSV field:

```text
stream_input_bytes
```

actually stored:

```text
num_words * component_n
```

That value is a number of bits, not bytes. The mistake does not affect latency,
throughput, CV, correctness, block-width selection, or LUT-size results, but it
could confuse tables, captions, and claim audits.

## New Schema

Raw and summary CSVs now use:

```text
stream_input_bits
stream_input_bytes
```

with:

```text
stream_input_bits = num_words * component_n
stream_input_bytes = ceil(stream_input_bits / 8)
```

## Code Changes

- `benchmarks/bench_long_stream_cache_width.py`
  - Emits both `stream_input_bits` and true `stream_input_bytes`.
- `scripts/migrate_long_stream_cache_width_schema.py`
  - Migrates existing raw CSVs without rerunning benchmarks.
  - Treats legacy `stream_input_bytes` as bits.
- `scripts/summarize_results.py`
  - Outputs both fields in main and replication summaries.
  - Keeps a legacy fallback for old raw rows.
- `tests/test_long_stream_cache_width.py`
  - Checks raw rows, CLI tiny output, summary rows, and plotting compatibility.
- `tests/test_result_summary.py`
  - Checks replication summary generation with the new schema.

## Migrated Artifacts

- `results/raw/long_stream_cache_width.csv`
- `results/raw/long_stream_cache_width_replication.csv`
- `results/summary/long_stream_cache_width_summary.csv`
- `results/summary/long_stream_cache_width_replication_summary.csv`

Example:

```text
legacy stream_input_bytes = 1342177200
new stream_input_bits     = 1342177200
new stream_input_bytes    = 167772150
```

## Audit

The migration compared current raw CSVs against the previous committed raw CSVs:

- Row counts were unchanged.
- All old measurement fields except the corrected stream-size schema matched
  exactly.
- Latency, throughput, CV, correctness, block width, and LUT bytes were not
  changed.

## Plot Status

`scripts/plot_experiment_round09_results.py` did not directly depend on
`stream_input_bytes`; it still runs under the new schema. The Round 9 diagnostic
figure was regenerated:

- `results/figures/experiment_round09_long_stream_cache_width.png`
- `results/figures/experiment_round09_long_stream_cache_width.pdf`

Only the PDF changed in git status after regeneration.

## Claim Safety

No result interpretation changed:

- L2 evidence remains mixed and should not be described as a stable strong
  claim.
- L3 evidence remains condition-specific to the eBCH-like long-stream workload.
- No BER, full OFEC decoder, full BCH algebraic decoder, or final paper
  conclusion was added.
- No new `BCH(511,484,r27)` profile was added.

## Commands

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

## Skills

- Used `results-analysis` for schema/value audit.
- Used `superpowers:test-driven-development` for failing tests before code
  changes.
- Used `superpowers:verification-before-completion` before final reporting.
- Did not use subagents because the task was small and tightly coupled.
