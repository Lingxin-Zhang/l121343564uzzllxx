# Latest Review Summary

Current round: Round 16 - Batch EventUpdate and HybridPlanner v1

## Modified Files

- `AGENTS.md`
- `README.md`
- `docs/bch_reference_notes.md`
- `linear_kernel/event_update.py`
- `linear_kernel/planner.py`
- `benchmarks/bench_bch_syndrome.py`
- `benchmarks/bench_event_update.py`
- `benchmarks/bench_planner.py`
- `scripts/run_all_benchmarks.py`
- `scripts/plot_results.py`
- `tests/test_event_update_many.py`
- `tests/test_planner.py`
- `results/raw/event_update.csv`
- `results/raw/planner.csv`
- refreshed benchmark CSV/PNG outputs
- `results/figures/event_update_comparison.png`
- `results/figures/planner_comparison.png`
- `review_gpt/latest.md`
- `review_gpt/round_16_summary.md`

## Implementation

- Implemented `EventUpdateKernel.update_many`.
- `update_many` supports `flip_count=0`, returns a new `np.uint8` array, and
  validates current-value and position shapes.
- Updated `bench_event_update.py` to compare:
  - `from_scratch.PackedBlockLUT.apply_many_packed`
  - `event_update.loop_update`
  - `event_update.batch_update_many`
- Implemented `HybridPlanner` v1 as a simple rule-based workload dispatcher.
- Added `benchmarks/bench_planner.py`.
- Hardened `bench_bch_syndrome.py` correctness checking from first chunk only
  to first, middle, and last chunks.
- Added event-update comparison and planner comparison plots.

## Generated Results

- `results/raw/event_update.csv` was generated.
- `results/raw/planner.csv` was generated.
- `results/figures/event_update_comparison.png` was generated.
- `results/figures/planner_comparison.png` was generated.
- Existing benchmark CSV/PNG outputs were refreshed by `run_all_benchmarks.py`.

Correctness summary:

- `event_update.csv` has 36 rows with `correctness_passed=True`.
- `planner.csv` has 108 rows with `correctness_passed=True`.
- `planner.csv` contains both `batch_syndrome` and `event_update` workloads.

## Verification

```text
python -m pytest -q
```

Passed: `204 passed, 1 skipped`.

```text
python scripts/run_all_benchmarks.py
```

Passed and generated CSV/PNG outputs.

```text
python scripts/plot_results.py
```

Passed and regenerated figures.

## Guardrails

- Full OFEC decoder implemented: no.
- Full BCH algebraic decoder implemented: no.
- BER simulation added: no.
- Paper conclusion or speedup claim added: no.
- External code copied: no.
- Real local paths committed: no.

## Notes

This is a lightweight reproducible benchmark run. `HybridPlanner` is a simple
rule baseline, not an optimal scheduler.
