# Round 15 Summary - Matrix-Source BCH Benchmark and Workloads

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

- Added matrix-source loading for `placeholder`, `galois_systematic_candidate`,
  and `random_fixed`.
- Kept the existing placeholder matrix unchanged.
- Updated BCH syndrome benchmark to record `matrix_source` and `matrix_shape`.
- Added chunked component-loop benchmark.
- Added event-update benchmark comparing from-scratch packed recomputation with
  `EventUpdateKernel.update`.
- Added matrix-source and workload correctness tests.
- Updated plotting for matrix-source aware BCH syndrome output plus component
  loop and event-update figures.

## Generated Artifacts

- `results/raw/bch_syndrome.csv`
- `results/raw/component_loop.csv`
- `results/raw/event_update.csv`
- `results/figures/bch_syndrome_throughput.png`
- `results/figures/component_loop_speedup.png`
- `results/figures/event_update_speedup.png`

`bch_syndrome.csv` contains both `placeholder` and
`galois_systematic_candidate`. Component-loop and event-update rows record
`correctness_passed=True`.

## Verification

```text
python -m pytest -q
```

Passed: `187 passed, 1 skipped`.

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
- HybridPlanner: not implemented.
- BER simulation: not added.
- Paper conclusion or speedup claim: not added.
- External code copied: no.
- Real local paths committed: no.
