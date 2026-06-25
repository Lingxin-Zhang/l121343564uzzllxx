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

The main aggregate timing field is `aggregate_latency_per_executed_unit_us`.
The older `latency_per_component_us` field is retained only for compatibility
with older CSV consumers.
