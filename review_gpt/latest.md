# Latest Review Summary

Current round: Round 17 - Result Freeze and Paper-style Figure/Table Export

## Modified Files

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `benchmarks/bench_planner.py`
- `docs/bch_reference_notes.md`
- `scripts/run_all_benchmarks.sh`
- `scripts/summarize_results.py`
- `scripts/export_paper_figures.py`
- `tests/test_result_summary.py`
- `results/raw/*.csv`
- `results/summary/*.csv`
- `results/figures/*.png`
- `results/figures/*.pdf`
- `results/paper_figures/*.png`
- `results/paper_figures/*.pdf`
- `review_gpt/latest.md`
- `review_gpt/round_17_summary.md`

## Implementation

- Hardened `benchmarks/bench_planner.py` for the event-update workload.
- The planner event-update benchmark now records:
  - `from_scratch.Naive.apply_many`
  - `from_scratch.PackedBlockLUT.apply_many_packed`
  - `HybridPlanner.update_many`
- Correctness checks compare from-scratch packed and planner update results
  against the Naive reference.
- Added `scripts/summarize_results.py` to convert raw benchmark CSV files into
  review-oriented summary CSV files under `results/summary/`.
- Added `scripts/export_paper_figures.py` to export compact figure/table-style
  benchmark views under `results/paper_figures/`.
- Updated the shell benchmark wrapper to run raw benchmarks, summaries, and
  paper-style figure export.
- Updated documentation to describe raw, summary, and paper-style artifact
  layers without adding paper conclusions.

## Generated Results

Summary CSV outputs:

- `results/summary/bch_syndrome_summary.csv`
- `results/summary/component_loop_summary.csv`
- `results/summary/event_update_summary.csv`
- `results/summary/planner_summary.csv`
- `results/summary/best_backend_by_workload.csv`

Paper-style figure outputs:

- `results/paper_figures/fig_bch_syndrome_throughput.png`
- `results/paper_figures/fig_bch_syndrome_throughput.pdf`
- `results/paper_figures/fig_component_loop_latency.png`
- `results/paper_figures/fig_component_loop_latency.pdf`
- `results/paper_figures/fig_event_update_comparison.png`
- `results/paper_figures/fig_event_update_comparison.pdf`
- `results/paper_figures/fig_planner_latency.png`
- `results/paper_figures/fig_planner_latency.pdf`

The raw benchmark CSV and raw figure outputs were refreshed. These are
lightweight reproducible benchmark artifacts for review, not paper conclusions.

## Result Notes

- `planner.csv` includes the requested event-update baselines:
  `from_scratch.Naive.apply_many`,
  `from_scratch.PackedBlockLUT.apply_many_packed`, and
  `HybridPlanner.update_many`.
- `planner_summary.csv` contains 144 summary rows and reports
  `correctness_all_true=True` for all rows.
- `event_update_summary.csv` reports `correctness_all_true=True` for all rows.
- The best-backend summary is derived mechanically from the raw CSV inputs and
  includes the note: `raw lightweight benchmark result; not a paper conclusion`.

## Verification

```text
python -m pytest -q
```

Passed: `208 passed, 1 skipped`.

```text
python scripts/run_all_benchmarks.py
```

Passed and regenerated raw CSV/figure outputs.

```text
python scripts/summarize_results.py
```

Passed and generated `results/summary/*.csv`.

```text
python scripts/export_paper_figures.py
```

Passed and generated `results/paper_figures/*.png` and `*.pdf`.

## Guardrails

- Full OFEC decoder implemented: no.
- Full BCH algebraic decoder implemented: no.
- BER simulation added: no.
- Paper conclusion or speedup claim added: no.
- External code copied: no.
- Real local paths committed: no.
- Reference validation or placeholder matrix status changed: no.
