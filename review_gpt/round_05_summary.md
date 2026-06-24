# Round 05 Summary: Micro-Benchmark Scripts and Initial Figures

## Modified Files

- `AGENTS.md`
- `.gitattributes`
- `README.md`
- `benchmarks/_common.py`
- `benchmarks/bench_block_width.py`
- `benchmarks/bench_density.py`
- `benchmarks/bench_batch.py`
- `scripts/plot_results.py`
- `scripts/run_all_benchmarks.py`
- `scripts/run_all_benchmarks.sh`
- `review_gpt/latest.md`
- `review_gpt/round_05_summary.md`

## Implementation

- Added shared benchmark helpers for deterministic setup, timing, CSV output, fastest-backend marking, and BlockLUT table-size accounting.
- Implemented block-width benchmark over widths `4, 6, 8, 10, 12, 14, 16, 18, 20`.
- Implemented density benchmark over densities `0.005, 0.01, 0.02, 0.05, 0.1, 0.5`.
- Implemented batch benchmark over batch sizes `1, 4, 16, 64, 256, 1024, 4096`.
- Implemented plotting to PNG and PDF for the three benchmark CSVs.
- Added a Python run-all script and kept the requested shell wrapper.
- Added `.gitattributes` so shell scripts keep LF line endings.
- Updated public documentation and workflow status without adding performance claims.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
49 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
generated results/raw/block_width.csv
generated results/raw/density.csv
generated results/raw/batch.csv
generated results/figures/block_width_vs_latency.png
generated results/figures/block_width_vs_latency.pdf
generated results/figures/density_backend_comparison.png
generated results/figures/density_backend_comparison.pdf
generated results/figures/batch_crossover.png
generated results/figures/batch_crossover.pdf
```

The local environment does not provide `bash`, so `scripts/run_all_benchmarks.sh`
was not executed directly here. The shell wrapper delegates to the Python runner.

## Known Issues

- `HybridPlanner` is not implemented.
- Generated CSV and figure files are local artifacts ignored by git.
- BlockLUT benchmark timing includes Python-loop overhead in current `apply_many`.

## Next Step

Review whether selected generated benchmark artifacts should be tracked, or keep
the repository limited to reproducible scripts.
