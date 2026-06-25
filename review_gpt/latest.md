# Latest Review Summary

Current round: supplemental experiment round 5.

## Goal

Final cleanup for result semantics. This round fixed two review issues:

1. `optical_workloads.csv` now records executed syndrome/event-update counts
   from actual prepared benchmark tasks, not directly from intended trace
   counts.
2. Lightweight component-decoder double-error exactness rows are now named
   `sampled_double_bit_errors`, not `all_double_bit_errors`.

This round does not add BER, a full OFEC decoder, a full BCH algebraic decoder,
or paper conclusions.

## Modified Files

- `benchmarks/bench_component_decoder_exactness.py`
- `benchmarks/bench_optical_workloads.py`
- `workloads/optical_traces.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round04_results.py`
- `tests/test_component_decoder_exactness.py`
- `tests/test_optical_workload_trace.py`
- `tests/test_result_summary.py`
- `docs/benchmark_semantics.md`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_05_summary.md`
- Refreshed `results/raw/*.csv`, `results/summary/*.csv`, and figures through
  the requested benchmark commands and `scripts/run_all_benchmarks.py`.

## Implementation Notes

- Optical workload executed counts are computed from prepared benchmark tasks:
  - `executed_syndrome_calls = sum(task["num_units"] for syndrome tasks)`
  - `executed_candidate_tests = sum(task["num_units"] for candidate tasks)`
  - `executed_event_updates = sum(task["num_units"] for event-update tasks)`
- The benchmark asserts executed counts do not exceed intended counts.
- Batch-capped workloads now expose the intended/executed difference in CSV.
- Component decoder exactness cases now include:
  - `double_error_coverage`
  - `num_possible_double_errors`
- Lightweight double-error rows use `sampled_double_bit_errors` with
  `double_error_coverage=sampled`.
- Full enumeration may use `all_double_bit_errors` only when all possible
  double-bit masks are evaluated.
- Round 4 diagnostic plotting now dynamically uses the test cases present in
  the CSV, so lightweight figures show `sampled_double_bit_errors`.

## Verification

- `python -m pytest -q`
  - Result: `273 passed, 1 skipped, 17 warnings`.
- `python -m benchmarks.bench_component_decoder_exactness --preset lightweight`
  - Result: passed.
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - Result: passed.
  - Odd-length `bch_255_239_r16` staircase rows were skipped by design.
- `python scripts/summarize_results.py`
  - Result: passed.
- `python scripts/plot_experiment_round04_results.py`
  - Result: passed.
- `python scripts/run_all_benchmarks.py`
  - Result: passed.

## Artifact Checks

- `results/raw/component_decoder_exactness.csv`: 24 rows.
- Component exactness test cases now include `sampled_double_bit_errors`.
- Lightweight double rows record:
  - `double_error_coverage=sampled`
  - `num_words=4096`
  - `num_possible_double_errors=32385`
- `exact_mismatch_count=0` for all component decoder exactness rows.
- `decoded_word_equal=True`, `correction_mask_equal=True`, `status_equal=True`,
  and `correctness_passed=True` for all component decoder exactness rows.
- `results/raw/optical_workloads.csv`: 160 rows.
- `intended_*` and `executed_*` fields are present.
- At least one batch-capped row has `executed_syndrome_calls <
  intended_syndrome_calls`.
- At least one batch-capped row has `executed_event_updates <
  intended_event_updates`.
- Executed counts are never greater than intended counts.

## Known Issues

- Lightweight component-decoder double-error exactness is sampled, not full
  enumeration.
- The component decoder benchmark remains an exactness/latency diagnostic only.
- Trace-level workloads remain clean-room kernel-call benchmarks, not full
  decoders or BER simulations.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No full product-code or staircase-code decoder.
- No external implementation code was copied.
- `external_refs/`, `paper/`, and `references/` were not committed.
