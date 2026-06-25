# Round 16 Summary - Batch EventUpdate and HybridPlanner v1

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

- Added `EventUpdateKernel.update_many`.
- Updated event-update benchmark with:
  - from-scratch packed recomputation;
  - per-word loop update;
  - batch `update_many`.
- Implemented `HybridPlanner` v1 as a simple rule-based dispatcher.
- Added planner benchmark for `batch_syndrome` and `event_update` workloads.
- Extended BCH syndrome benchmark correctness checks to first, middle, and
  last chunks.
- Added event-update and planner tests.

## Artifacts

- `results/raw/event_update.csv`
- `results/raw/planner.csv`
- `results/figures/event_update_comparison.png`
- `results/figures/planner_comparison.png`

`event_update.csv` records 36 correctness-passing rows. `planner.csv` records
108 correctness-passing rows.

## Verification

```text
python -m pytest -q
```

Passed: `204 passed, 1 skipped`.

```text
python scripts/run_all_benchmarks.py
```

Passed.

```text
python scripts/plot_results.py
```

Passed.

## Guardrails

- Complete OFEC decoder: not implemented.
- Complete BCH algebraic decoder: not implemented.
- BER simulation: not added.
- Paper conclusion or speedup claim: not added.
- External code copied: no.
- Real local paths committed: no.
