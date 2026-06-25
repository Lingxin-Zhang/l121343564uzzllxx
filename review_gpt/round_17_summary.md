# Round 17 Summary - Result Freeze and Paper-style Figure/Table Export

## Scope

This round froze the current lightweight benchmark outputs, added summary CSV
generation, added paper-style figure export, and hardened the planner benchmark
event-update workload. It did not add new decoding logic or paper claims.

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

## Implementation Details

- `benchmarks/bench_planner.py` now includes both from-scratch event-update
  baselines:
  - `from_scratch.Naive.apply_many`
  - `from_scratch.PackedBlockLUT.apply_many_packed`
- `HybridPlanner.update_many` remains included as the planner method.
- Planner correctness is checked against the Naive reference.
- `scripts/summarize_results.py` reads raw benchmark CSV files and writes:
  - `bch_syndrome_summary.csv`
  - `component_loop_summary.csv`
  - `event_update_summary.csv`
  - `planner_summary.csv`
  - `best_backend_by_workload.csv`
- `scripts/export_paper_figures.py` reads summary CSV files and writes compact
  PNG/PDF figure exports under `results/paper_figures/`.
- README and AGENTS were updated to document raw, summary, and paper-style
  benchmark artifact layers.

## Tests and Commands

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

Passed and generated summary CSV outputs.

```text
python scripts/export_paper_figures.py
```

Passed and generated paper-style PNG/PDF figure outputs.

## Known Issues

- The benchmark outputs are lightweight reproducible artifacts, not paper
  conclusions.
- `HybridPlanner` remains a simple v1 rule-based planner.
- `PackedBatch` is still a correctness-first NumPy implementation, not a true
  bit-packed optimized backend.

## Next Steps

- Review whether summary fields are sufficient for external code review.
- If needed, add confidence intervals or repeated-run metadata in a later round.
- Keep reference validation and full decoder work separate from benchmark export.

## Guardrails

- Full OFEC decoder implemented: no.
- Full BCH algebraic decoder implemented: no.
- BER simulation added: no.
- Paper conclusion or speedup claim added: no.
- External code copied: no.
- Real local paths committed: no.
