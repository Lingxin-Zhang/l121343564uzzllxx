# Latest Review Summary

Current round: Round 15 - Matrix-Source BCH Benchmark and Workloads

## Modified Files

- `AGENTS.md`
- `README.md`
- `codes/__init__.py`
- `codes/matrix_sources.py`
- `benchmarks/_common.py`
- `benchmarks/bench_bch_syndrome.py`
- `benchmarks/bench_component_loop.py`
- `benchmarks/bench_event_update.py`
- `scripts/run_all_benchmarks.py`
- `scripts/run_all_benchmarks.sh`
- `scripts/plot_results.py`
- `tests/test_matrix_sources.py`
- `tests/test_event_update_benchmark_logic.py`
- `docs/bch_reference_notes.md`
- `results/raw/bch_syndrome.csv`
- `results/raw/component_loop.csv`
- `results/raw/event_update.csv`
- refreshed benchmark CSV/PNG outputs
- `review_gpt/latest.md`
- `review_gpt/round_15_summary.md`

## Implementation

- Added `codes.matrix_sources.get_matrix_source()`.
- Supported matrix sources:
  - `placeholder`
  - `galois_systematic_candidate`
  - `random_fixed`
- Updated generic benchmark matrix creation to use `random_fixed`.
- Updated `bench_bch_syndrome.py` with `--matrix-source`, `matrix_source`,
  and `matrix_shape`.
- Added `bench_component_loop.py` for repeated chunked component syndrome
  computation.
- Added `bench_event_update.py` for sparse bit-flip syndrome update timing.
- Updated run-all scripts so BCH syndrome runs both `placeholder` and
  `galois_systematic_candidate`.
- Added plots:
  - `results/figures/component_loop_speedup.png`
  - `results/figures/event_update_speedup.png`
- Updated BCH syndrome plot to distinguish `matrix_source`.

## Generated Results

- `results/raw/bch_syndrome.csv` was generated with both matrix sources:
  - `placeholder`: 24 rows
  - `galois_systematic_candidate`: 24 rows
- `results/raw/component_loop.csv` was generated.
- `results/raw/event_update.csv` was generated.
- `results/figures/component_loop_speedup.png` was generated.
- `results/figures/event_update_speedup.png` was generated.
- `results/figures/bch_syndrome_throughput.png` was regenerated with
  matrix-source aware labels.

Correctness status:

- Component-loop CSV has `correctness_passed=True` for all 36 rows.
- Event-update CSV has `correctness_passed=True` for all 24 rows.
- Backend outputs are checked against Naive/Packed reference outputs before
  timing rows are recorded.

## Verification

```text
python -m pytest -q
```

Passed: `187 passed, 1 skipped`.

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
- HybridPlanner implemented: no.
- BER simulation added: no.
- Paper conclusion or speedup claim added: no.
- External code copied: no.
- Real local paths committed: no.

## Notes

This is a lightweight reproducible benchmark run. The figures are raw
measurement artifacts for review, not paper conclusions.
