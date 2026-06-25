# Supplemental Experiment Round 4 Summary

## Goal

This round implemented BCH-component-style BDD LUT exactness diagnostics and
cleaned benchmark result semantics. It remains component-kernel level only: no
BER, no full OFEC decoder, no full BCH algebraic decoder, and no paper
conclusions.

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
- `results/raw/*.csv`
- `results/summary/*.csv`
- `results/figures/*.png` and generated PDF counterparts

## Implementation Summary

- Added a deterministic `BDDLUTDecoder` for t<=2 syndrome lookup.
- Added strict collision detection for zero/single/double syndrome entries.
- Added single and batch decode APIs for syndromes and received words.
- Added `bench_component_decoder_exactness.py` with Naive, PackedBatch,
  PackedBlockLUT, and HybridPlanner syndrome backends.
- Added component exactness cases for zero, single, double, triple, random
  low-weight, and random received-word batches.
- Updated candidate-testing CSV semantics with `output_mode`,
  `selected_backend`, and `selected_backend_reason`.
- Added both planner paths in candidate testing:
  `HybridPlanner.apply_many` and `HybridPlanner.apply_many_packed`.
- Updated optical workload CSV semantics with intended/executed counters and
  `aggregate_latency_per_executed_unit_us`.
- Renamed the integrated event-update method to
  `Naive+EventUpdate.integrated` in regenerated outputs.
- Documented known-hit candidate collisions and reference-only HUAWEI boundary.

## Generated Artifacts

- `results/raw/component_decoder_exactness.csv`: 24 rows.
- `results/summary/component_decoder_exactness_summary.csv`: 24 rows.
- `results/figures/experiment_round04_component_decoder_exactness.png`
- `results/figures/experiment_round04_component_decoder_exactness.pdf`
- Refreshed candidate-testing and optical-workload CSV/summary artifacts.
- Refreshed diagnostic figures through `scripts/run_all_benchmarks.py`.

## Verification

- `python -m pytest -q`
  - `271 passed, 1 skipped, 16 warnings`
- `python -m benchmarks.bench_component_decoder_exactness --preset lightweight`
  - passed
- `python -m benchmarks.bench_candidate_testing --preset lightweight`
  - passed
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - passed; odd-length `bch_255_239_r16` staircase rows skipped by design
- `python scripts/summarize_results.py`
  - passed
- `python scripts/plot_experiment_round04_results.py`
  - passed
- `python scripts/plot_experiment_round02_results.py`
  - passed
- `python scripts/run_all_benchmarks.py`
  - passed

## Artifact Checks

- Component decoder exactness: `exact_mismatch_count = 0` for all rows.
- Component decoder exactness: `correctness_passed=True` for all rows.
- Candidate testing includes both planner packed and unpacked rows.
- Optical workload CSV uses `Naive+EventUpdate.integrated`.
- Old `EventUpdate.integrated` is absent from regenerated optical CSV.
- Executed candidate-test counts are never greater than intended counts.

## Known Issues

- BDD LUT is limited to t<=2.
- The component decoder benchmark is an exactness/latency diagnostic only.
- HybridPlanner remains a simple rule-based baseline.
- Figures are diagnostic artifacts and are not paper conclusions.

## Explicitly Not Done

- No BER simulation.
- No full OFEC decoder.
- No full BCH algebraic decoder.
- No full product-code or staircase-code decoder.
- No GPU work.
- No paper text or speedup claim.
- No external implementation code was copied.
- `external_refs/`, `paper/`, and `references/` were not committed.
