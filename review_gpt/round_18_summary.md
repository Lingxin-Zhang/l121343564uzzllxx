# Round 18 Summary - Round 2 Cache/Profile Diagnostics

## Scope

This round implemented only the requested Round 2 work:

- `r <= 32` packed output support
- `CodeProfile`
- `CacheProfile`
- cache-aware lightweight benchmark
- code-profile scaling lightweight benchmark
- Round 2 diagnostic summaries and figures

Round 3, Round 4, and Round 5 were not executed.

## Code Changes

- `linear_kernel/matrix_utils.py`
  - Added `uint32` pack/unpack helpers for `r <= 32`.
- `linear_kernel/packed_block_lut.py`
  - Extended `PackedBlockLUTKernel` to use `uint16` for `r <= 16` and `uint32`
    for `17 <= r <= 32`.
- `linear_kernel/cache_profile.py`
  - Added cache metadata and LUT footprint estimation.
- `codes/code_profiles.py`
  - Added small named GF(2) workload profiles for scaling diagnostics.
- `benchmarks/bench_cache_aware.py`
  - Added lightweight/full CLI presets for block-width, density, batch-size,
    and cache-footprint diagnostics.
- `benchmarks/bench_code_profiles.py`
  - Added lightweight/full CLI presets for comparing backend behavior across
    named code profiles.
- `scripts/summarize_results.py`
  - Added summaries for `cache_aware.csv` and `code_profile_scaling.csv`.
- `scripts/plot_round2_results.py`
  - Added two diagnostic figure exports.
- `README.md` and `AGENTS.md`
  - Updated public documentation for Round 2 diagnostics and `r <= 32`
    `PackedBlockLUTKernel` support.

## Tests

- `python -m pytest -q`
  - Result: `233 passed, 1 skipped`

Additional focused tests were added for:

- `uint32` pack/unpack correctness
- `PackedBlockLUTKernel` correctness for `r=17` and `r=32`
- code-profile metadata and matrix generation
- cache-profile footprint estimation
- benchmark row summarization helpers

## Benchmarks and Summaries

Commands run:

- `python -m benchmarks.bench_cache_aware --preset lightweight`
- `python -m benchmarks.bench_code_profiles --preset lightweight`
- `python scripts/summarize_results.py`
- `python scripts/plot_round2_results.py`

Generated or updated:

- `results/raw/cache_aware.csv`
- `results/raw/code_profile_scaling.csv`
- `results/summary/cache_aware_summary.csv`
- `results/summary/code_profile_scaling_summary.csv`
- `results/summary/best_backend_by_workload.csv`
- `results/figures/round2_cache_aware_latency.png`
- `results/figures/round2_cache_aware_latency.pdf`
- `results/figures/round2_code_profile_scaling.png`
- `results/figures/round2_code_profile_scaling.pdf`

## Known Issues

- `PackedBlockLUT.apply_many_packed` is still a correctness-first Python
  implementation with Python-side mask extraction.
- Lightweight benchmark results are diagnostic only and should not be used as
  broad performance claims.
- Synthetic code profiles are not standards references.

## Next Suggested Code Tasks

- Review whether `PackedBlockLUT.apply_many_packed` should get a vectorized
  mask-extraction path before any broader benchmark.
- Add explicit lightweight/full preset documentation if the benchmark matrix
  grows.
- Keep any future product-like or oFEC-like workload work separate from this
  Round 2 diagnostic path.
