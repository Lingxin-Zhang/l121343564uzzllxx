# Latest Review Summary

Current round: supplemental experiment round 4.

## Goal

Implement a clean bounded-distance component decoder LUT, add component-decoder
exactness measurement, and clean up result semantics for candidate-testing and
trace-level workload CSV files. This round remains component-kernel level only:
no BER, no full OFEC decoder, no full BCH algebraic decoder, no full product or
staircase decoder, and no paper conclusions.

## Modified Files

- `decoders/bdd_lut.py`
- `decoders/__init__.py`
- `benchmarks/bench_component_decoder_exactness.py`
- `benchmarks/bench_candidate_testing.py`
- `benchmarks/bench_optical_workloads.py`
- `workloads/optical_traces.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round02_results.py`
- `scripts/plot_experiment_round04_results.py`
- `scripts/run_all_benchmarks.py`
- `tests/test_bdd_lut_decoder.py`
- `tests/test_component_decoder_exactness.py`
- `tests/test_candidate_testing.py`
- `tests/test_optical_workload_trace.py`
- `tests/test_result_summary.py`
- `tests/test_benchmark_semantics.py`
- `docs/benchmark_semantics.md`
- `docs/reference_inspection_notes.md`
- `README.md`
- Updated `results/raw/*.csv`, `results/summary/*.csv`, and diagnostic figures.

## Implementation Notes

- `BDDLUTDecoder` now builds a deterministic t<=2 syndrome LUT from a GF(2)
  matrix.
- Syndrome 0 maps to `no_error`; single and double error syndromes map to
  `corrected`; unknown syndromes map to `failure`.
- Strict collision checking is enabled by default. Non-strict mode keeps the
  first entry and records `collision_count`.
- `decode_syndrome`, `decode_syndromes`, `decode_word`, and `decode_words`
  support unpacked syndromes, packed syndrome batches, and received-word decode.
- `bench_component_decoder_exactness.py` compares:
  - `NaiveGF2Kernel.apply_many`
  - `PackedBatchGF2Kernel.apply_many`
  - `PackedBlockLUTKernel.apply_many_packed`
  - `HybridPlanner.apply_many_packed`
- Component decoder exactness cases include zero, all singles, sampled doubles,
  sampled triples, random low-weight errors, and random received batches.
- `candidate_testing.csv` now records `output_mode`, `selected_backend`, and
  `selected_backend_reason`.
- Candidate testing now includes both `HybridPlanner.apply_many` and
  `HybridPlanner.apply_many_packed`.
- `optical_workloads.csv` now records intended/executed counts separately for
  syndrome calls, candidate tests, and event updates.
- The main optical aggregate metric is now
  `aggregate_latency_per_executed_unit_us`; `latency_per_component_us` remains
  for compatibility only.
- New CSV rows use `Naive+EventUpdate.integrated`; old
  `EventUpdate.integrated` is absent from the regenerated optical CSV.
- Known-hit candidate semantics are documented: `matches_found` is at least
  one and can exceed one when multiple candidate masks share a syndrome.
- HUAWEI-OFEC-Tao is documented as reference-only engineering context.

## Generated Artifacts

- `results/raw/component_decoder_exactness.csv`: 24 rows.
- `results/summary/component_decoder_exactness_summary.csv`: 24 rows.
- `results/figures/experiment_round04_component_decoder_exactness.png`
- `results/figures/experiment_round04_component_decoder_exactness.pdf`
- Refreshed candidate-testing and optical-workload raw/summary CSV files.
- Refreshed Round 2 optical diagnostic figures using executed-unit latency.
- `scripts/run_all_benchmarks.py` now includes the Round 4 benchmark and figure.

## Verification

- `python -m pytest -q`
  - Result: `271 passed, 1 skipped, 16 warnings`.
- `python -m benchmarks.bench_component_decoder_exactness --preset lightweight`
  - Result: passed, wrote `results/raw/component_decoder_exactness.csv`.
- `python -m benchmarks.bench_candidate_testing --preset lightweight`
  - Result: passed, wrote `results/raw/candidate_testing.csv`.
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - Result: passed, wrote aggregate and breakdown CSV files.
  - Odd-length `bch_255_239_r16` staircase rows were skipped by design.
- `python scripts/summarize_results.py`
  - Result: passed, wrote `component_decoder_exactness_summary.csv`.
- `python scripts/plot_experiment_round04_results.py`
  - Result: passed, wrote PNG/PDF diagnostic figure.
- `python scripts/plot_experiment_round02_results.py`
  - Result: passed, regenerated Round 2 diagnostic figures.
- `python scripts/run_all_benchmarks.py`
  - Result: passed.

## Artifact Checks

- `component_decoder_exactness.csv` has `exact_mismatch_count = 0` for all rows.
- `correctness_passed=True` for all component decoder exactness rows.
- `candidate_testing.csv` includes planner packed and unpacked rows.
- `optical_workloads.csv` includes `Naive+EventUpdate.integrated`.
- `optical_workloads.csv` does not include old `EventUpdate.integrated`.
- Executed candidate-test counts are never greater than intended counts.

## Known Issues

- BDD LUT correction is bounded to t<=2 and is syndrome-table based.
- The component decoder benchmark is an exactness/latency diagnostic, not a BER
  or full-decoder benchmark.
- `HybridPlanner` remains a simple reproducible rule baseline.
- The generated figures are diagnostic artifacts, not paper conclusions.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No full product-code or staircase-code decoder.
- No GPU work.
- No paper-text or speedup claims.
- No external implementation code was copied.
- `external_refs/`, `paper/`, and `references/` were not committed.
