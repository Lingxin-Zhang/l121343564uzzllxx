# Supplemental Experiment Round 5 Summary

## Goal

Final cleanup for result semantics after component-decoder exactness landed.
This round fixes executed-count semantics in trace-level workloads and clarifies
that lightweight double-error exactness is sampled, not full enumeration.

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
- Refreshed CSV/summary/figure artifacts under `results/`.

## Implementation Summary

- Optical workload executed counts now come from actual prepared benchmark
  tasks rather than from uncapped trace-intended counts.
- The benchmark records and validates:
  - `executed_syndrome_calls <= intended_syndrome_calls`
  - `executed_candidate_tests <= intended_candidate_tests`
  - `executed_event_updates <= intended_event_updates`
- Batch-capped workloads now visibly show executed counts smaller than intended
  counts in `optical_workloads.csv`.
- Component decoder exactness now records `double_error_coverage` and
  `num_possible_double_errors`.
- Lightweight double-error rows are named `sampled_double_bit_errors`.
- Full double-error rows may be named `all_double_bit_errors` only when every
  possible double-bit error mask is enumerated.
- Round 4 diagnostic figure generation now uses the test-case names present in
  the CSV.

## Verification

- `python -m pytest -q`
  - `273 passed, 1 skipped, 17 warnings`
- `python -m benchmarks.bench_component_decoder_exactness --preset lightweight`
  - passed
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - passed
- `python scripts/summarize_results.py`
  - passed
- `python scripts/plot_experiment_round04_results.py`
  - passed
- `python scripts/run_all_benchmarks.py`
  - passed

## Artifact Checks

- `results/raw/component_decoder_exactness.csv` has 24 rows.
- The lightweight double-error case is `sampled_double_bit_errors`.
- Lightweight double rows record `double_error_coverage=sampled`,
  `num_words=4096`, and `num_possible_double_errors=32385`.
- `exact_mismatch_count=0` for all component decoder exactness rows.
- `decoded_word_equal`, `correction_mask_equal`, `status_equal`, and
  `correctness_passed` are all true for all component decoder exactness rows.
- `results/raw/optical_workloads.csv` has intended/executed fields for
  syndrome calls, candidate tests, and event updates.
- Batch-capped workload rows show executed syndrome/event-update counts smaller
  than intended counts.

## Known Issues

- Lightweight double-error exactness is sampled by design.
- Trace-level workloads are kernel-call diagnostics only.
- No BER or full decoder result is produced in this round.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No full product-code or staircase-code decoder.
- No paper text or speedup claim.
- No external repository code was copied.
- `external_refs/`, `paper/`, and `references/` were not committed.
