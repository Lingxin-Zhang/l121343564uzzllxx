# Latest Review Summary

Current round: supplemental experiment round 3.

## Goal

Fix trace-level workload semantics, candidate-testing target semantics,
HybridPlanner dispatch rules, and optical-workload reporting. This round remains
trace-level only: no BER, no full product-code decoder, no full staircase
decoder, no full OFEC decoder, and no Chase-Pyndiah decoder.

## Modified Files

- `workloads/optical_traces.py`
- `benchmarks/bench_candidate_testing.py`
- `benchmarks/bench_optical_workloads.py`
- `benchmarks/bench_planner.py`
- `linear_kernel/planner.py`
- `scripts/summarize_results.py`
- `scripts/plot_experiment_round02_results.py`
- `tests/test_optical_workload_trace.py`
- `tests/test_candidate_testing.py`
- `tests/test_planner.py`
- `docs/reference_inspection_notes.md`
- `results/raw/*.csv`
- `results/summary/*.csv`
- `results/figures/*.png` and generated PDF counterparts

## Implementation Notes

- `product_like` now records that `num_blocks` means
  `num_components_per_dimension`.
- `product_like` syndrome calls are modeled as row plus column component
  batches, so total syndrome calls per iteration are
  `2 * num_components_per_dimension`.
- `staircase_like` now requires even component length `n`.
- `staircase_like` now records `half_width`, `active_blocks`,
  `active_components`, and `trace_model="clean_room_half_block_window"`.
- `staircase_like` active component count is now
  `active_blocks * (n // 2)`.
- Lightweight optical workload execution explicitly skipped the odd-length
  `bch_255_239_r16` staircase profile; only the even-length profile appears in
  the staircase rows.
- `ofec_like` candidate fields now distinguish:
  - `candidates_per_component`
  - `intended_candidate_tests`
  - `executed_candidate_tests`
  - optional `max_candidate_tests_per_event`
- `candidate_testing` now supports `--target-mode zero|known_hit`, with
  `known_hit` as the default.
- `known_hit` chooses a candidate-generated target syndrome, so every generated
  row has at least one matching candidate across all backends.
- `HybridPlanner` now uses simple rule-based dispatch:
  - single sparse input -> `SparseXorKernel`
  - single dense input -> `PackedBlockLUTKernel`
  - large packed batch -> `PackedBlockLUTKernel`
  - large unpacked batch -> `PackedBatchGF2Kernel`
  - small batch -> `PackedBlockLUTKernel`
  - event update -> `EventUpdateKernel`
- `planner.csv` now records `selected_backend` for HybridPlanner rows.
- `bench_optical_workloads.py` now writes both:
  - `results/raw/optical_workloads.csv`
  - `results/raw/optical_workload_breakdown.csv`
- `scripts/summarize_results.py` now writes:
  - `results/summary/optical_workload_breakdown_summary.csv`
- `scripts/plot_experiment_round02_results.py` now writes:
  - `results/figures/experiment_round02_optical_workload_breakdown.png`

## Verification

- `python -m pytest -q`
  - Result: `257 passed, 1 skipped, 16 warnings`
- `python -m benchmarks.bench_candidate_testing --preset lightweight`
  - Result: passed, wrote `results/raw/candidate_testing.csv`
- `python -m benchmarks.bench_optical_workloads --preset lightweight`
  - Result: passed, wrote aggregate and breakdown CSV files
  - Explicitly skipped odd-length staircase profile rows
- `python scripts/summarize_results.py`
  - Result: passed, wrote summary CSV files including optical breakdown summary
- `python scripts/plot_experiment_round02_results.py`
  - Result: passed, wrote candidate, workload, and breakdown diagnostic figures
- `python scripts/run_all_benchmarks.py`
  - Result: passed

## Artifact Checks

- `results/raw/candidate_testing.csv`: 180 rows, `target_mode=known_hit`.
- Minimum `matches_found` in candidate testing: 1.
- `results/raw/optical_workloads.csv`: 160 rows.
- `results/raw/optical_workload_breakdown.csv`: 320 rows.
- `results/summary/optical_workload_breakdown_summary.csv`: 40 rows.
- Breakdown task kinds present: `syndrome`, `candidate_test`, `event_update`.
- `results/raw/planner.csv` includes HybridPlanner selected backend values:
  `PackedBlockLUTKernel` and `EventUpdateKernel`.

## Known Issues

- These workload traces are clean-room synthetic component-kernel traces only.
- The optical workload benchmark still uses lightweight caps for candidate
  execution and records intended versus executed counts.
- HybridPlanner is a reproducible rule-based baseline, not an optimal planner.
- The generated figures are diagnostic figures, not paper conclusions.

## Explicitly Not Done

- No BER simulation.
- No full product-code decoder.
- No full staircase-code decoder.
- No full OFEC decoder.
- No full Chase-Pyndiah decoder.
- No external implementation code was copied.
- `external_refs/` was not committed.

## Next Steps

- Review whether the lightweight cap for candidate tests should become a
  CLI-visible preset policy in future full runs.
- If planner evaluation needs unpacked batch behavior, add a planner benchmark
  row for `HybridPlanner.apply_many` in addition to the packed batch row.
