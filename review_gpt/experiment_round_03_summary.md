# Supplemental Experiment Round 3 Summary

## Scope

This round fixed trace-level workload semantics and benchmark reporting logic.
It did not implement BER, full product-code decoding, full staircase-code
decoding, full OFEC decoding, or a Chase-Pyndiah decoder.

## Changes

- `product_like`
  - Clarified `num_blocks` as `num_components_per_dimension`.
  - Kept row and column component batches per iteration.
  - Total syndrome calls now match
    `2 * num_components_per_dimension * iterations`.

- `staircase_like`
  - Requires even component length.
  - Uses `half_width = n // 2`.
  - Uses `active_blocks = min(num_blocks, window_len)`.
  - Uses `active_components = active_blocks * half_width`.
  - Records the clean-room half-block window trace model in metadata.

- `ofec_like`
  - Renamed candidate semantics around `candidates_per_component`.
  - Records intended and executed candidate tests separately.
  - Supports a lightweight cap through `max_candidate_tests_per_event`.

- Candidate testing benchmark
  - Added `--target-mode zero|known_hit`.
  - Default target mode is `known_hit`.
  - Known-hit rows require at least one matching candidate and consistent
    `matches_found` across backends.

- HybridPlanner
  - Dispatches sparse single inputs to `SparseXorKernel`.
  - Dispatches event updates to `EventUpdateKernel`.
  - Dispatches large unpacked batches to `PackedBatchGF2Kernel`.
  - Dispatches packed batches and small batches to `PackedBlockLUTKernel`.
  - `planner.csv` records selected backends for HybridPlanner rows.

- Optical workload benchmark
  - Keeps aggregate `optical_workloads.csv`.
  - Adds `optical_workload_breakdown.csv` with per-task metrics for
    `syndrome`, `candidate_test`, and `event_update`.

- Summary and plotting
  - Added `optical_workload_breakdown_summary.csv`.
  - Added a diagnostic task-breakdown figure.

## Tests

- `python -m pytest -q`
  - Result: `257 passed, 1 skipped, 16 warnings`.

New or updated coverage includes:

- product row/column calls and total syndrome call count.
- staircase odd-length rejection.
- staircase half-block active component count.
- ofec-like intended/executed candidate test counts.
- known-hit candidate target with at least one match.
- candidate mismatch fail-fast behavior.
- planner sparse single-input dispatch.
- planner event-update dispatch.
- planner batch output-mode dispatch.

## Benchmark Commands

- `python -m benchmarks.bench_candidate_testing --preset lightweight`
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
- `python scripts/summarize_results.py`
- `python scripts/plot_experiment_round02_results.py`
- `python scripts/run_all_benchmarks.py`

All commands completed successfully.

## Generated Artifacts

- `results/raw/candidate_testing.csv`
- `results/raw/optical_workloads.csv`
- `results/raw/optical_workload_breakdown.csv`
- `results/summary/candidate_testing_summary.csv`
- `results/summary/optical_workloads_summary.csv`
- `results/summary/optical_workload_breakdown_summary.csv`
- `results/figures/experiment_round02_candidate_testing.png`
- `results/figures/experiment_round02_optical_workloads.png`
- `results/figures/experiment_round02_optical_workload_breakdown.png`

`run_all_benchmarks.py` also refreshed the existing lightweight raw, summary,
and diagnostic figure artifacts.

## Artifact Checks

- Candidate testing rows: 180.
- Candidate testing target mode: `known_hit`.
- Minimum candidate `matches_found`: 1.
- Optical workload aggregate rows: 160.
- Optical workload breakdown rows: 320.
- Optical workload breakdown task kinds: `syndrome`, `candidate_test`,
  `event_update`.
- Odd-length staircase profile rows are skipped explicitly.

## Reference Handling

- The local Chase-Pyndiah demo was inspected only for clean-room design
  implications.
- No external source code was copied.
- No external reference repository was committed.

## Known Issues

- Lightweight candidate caps mean `intended_candidate_tests` can be larger than
  `executed_candidate_tests`.
- HybridPlanner remains a simple deterministic rule baseline.
- Figures are diagnostic and should not be used as final paper conclusions.
