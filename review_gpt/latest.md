# Latest Review Summary

Current round: Round 05 - Micro-Benchmark Scripts and Initial Figures

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

- Added shared benchmark helpers for deterministic matrices, density-controlled batches, repeated timing, CSV writing, fastest-backend marking, and BlockLUT table-size accounting.
- Implemented block-width micro-benchmark for `Naive`, `SparseXor`, and `BlockLUT`.
- Implemented density micro-benchmark for `Naive`, `SparseXor`, `BlockLUT`, and `PackedBatch`.
- Implemented batch-size crossover micro-benchmark for `Naive.apply_many`, `BlockLUT.apply_many`, and `PackedBatch.apply_many`.
- Implemented plotting for block-width latency, density comparison, and batch crossover.
- Added Python run-all entry point and kept the shell wrapper as a thin launcher.
- Added `.gitattributes` so shell scripts keep LF line endings.
- Updated public docs to describe generic benchmark scripts without performance claims.

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
- Push to `origin/main` failed in this environment after repeated attempts due
  to GitHub HTTPS connection resets/timeouts. The GitHub connector can read the
  repository but does not have push permission.

## Next Step

Review the generated CSVs and decide whether to track selected benchmark
artifacts or keep them as local reproducible outputs. Retry `git push -u origin
main` when GitHub network access is stable.
