# Benchmark Semantics

This note records code-level benchmark semantics for reproducibility review.

## Candidate Testing Known-Hit Mode

In known-hit mode, matches_found is guaranteed to be at least one. It may exceed one because different candidate masks can share the same syndrome.
The same rule applies to the CSV field `matches_found`.
Multiple matches are therefore not treated as a correctness error by the
candidate-testing benchmark.

## Trace-Level Workloads

Trace-level workload benchmarks report intended and executed counts separately:

- `intended_syndrome_calls` / `executed_syndrome_calls`
- `intended_candidate_tests` / `executed_candidate_tests`
- `intended_event_updates` / `executed_event_updates`

`intended_*` fields come from the clean-room trace design. `executed_*` fields
come from the actual benchmark task batches prepared for execution:

- `executed_syndrome_calls` is the sum of `num_units` for syndrome tasks.
- `executed_candidate_tests` is the sum of `num_units` for candidate-test
  tasks.
- `executed_event_updates` is the sum of `num_units` for event-update tasks.

When a workload event is capped by `batch_size` or by
`max_candidate_tests_per_event`, the executed count can be smaller than the
intended count. The CSV keeps both values.

The main aggregate timing field is `aggregate_latency_per_executed_unit_us`.
The older `latency_per_component_us` field is retained only for compatibility
with older CSV consumers.

## Component Decoder Exactness Cases

The component decoder exactness benchmark records whether double-bit cases are
sampled or fully enumerated:

- Lightweight runs use `sampled_double_bit_errors` when only a subset of all
  double-bit error masks is evaluated.
- Full runs may use `all_double_bit_errors` only when all possible double-bit
  error masks are enumerated.

The CSV fields `double_error_coverage` and `num_possible_double_errors` make
this explicit.
