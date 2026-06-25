# Latest Review Summary

Current round: Round 18 - Round 2 cache/profile diagnostics only

## Scope

This round completed only the requested Round 2 work:

- `r <= 32` packed output support for `PackedBlockLUTKernel`
- `CodeProfile`
- `CacheProfile`
- cache-aware lightweight benchmark
- code-profile scaling lightweight benchmark
- Round 2 diagnostic summary and figures

Round 3, Round 4, and Round 5 work was not executed.

## Modified Files

- `linear_kernel/matrix_utils.py`
- `linear_kernel/packed_block_lut.py`
- `linear_kernel/cache_profile.py`
- `codes/code_profiles.py`
- `benchmarks/bench_cache_aware.py`
- `benchmarks/bench_code_profiles.py`
- `scripts/summarize_results.py`
- `scripts/plot_round2_results.py`
- `tests/test_packed_uint32.py`
- `tests/test_code_profiles.py`
- `tests/test_cache_profile.py`
- `tests/test_round2_benchmark_tools.py`
- `tests/test_correctness.py`
- `README.md`
- `AGENTS.md`
- `review_gpt/latest.md`
- `review_gpt/round_18_summary.md`

## Implementation

- Added `uint32` bit-packing helpers:
  - `pack_bits_to_uint32`
  - `unpack_uint32_to_bits`
  - `pack_batch_bits_to_uint32`
- Extended `PackedBlockLUTKernel` from `r <= 16` to `r <= 32`.
  - `r <= 16` uses `np.uint16`.
  - `17 <= r <= 32` uses `np.uint32`.
  - `apply()` and `apply_many()` still return unpacked `np.uint8` bits.
  - `apply_packed()` and `apply_many_packed()` return packed scalars/arrays.
- Added `CacheProfile` and LUT cache-footprint estimation utilities.
- Added named `CodeProfile` workloads for shape-scaling diagnostics.
- Added two lightweight benchmark modules:
  - `benchmarks.bench_cache_aware`
  - `benchmarks.bench_code_profiles`
- Added Round 2 plotting script:
  - `scripts/plot_round2_results.py`
- Updated result summarization to cover the new CSV files.
- Updated public documentation to mention Round 2 diagnostics and `r <= 32`
  packed output support.
- Updated public `AGENTS.md` with generic local-reference guidance; concrete
  machine-local paths remain in ignored `AGENTS.local.md` and are not committed.

## Generated Artifacts

- `results/raw/cache_aware.csv`
- `results/raw/code_profile_scaling.csv`
- `results/summary/cache_aware_summary.csv`
- `results/summary/code_profile_scaling_summary.csv`
- `results/summary/best_backend_by_workload.csv`
- `results/figures/round2_cache_aware_latency.png`
- `results/figures/round2_cache_aware_latency.pdf`
- `results/figures/round2_code_profile_scaling.png`
- `results/figures/round2_code_profile_scaling.pdf`

## Verification

- `python -m pytest -q`
  - Result: `233 passed, 1 skipped`
- `python -m benchmarks.bench_cache_aware --preset lightweight`
  - Result: completed and wrote `results/raw/cache_aware.csv`
- `python -m benchmarks.bench_code_profiles --preset lightweight`
  - Result: completed and wrote `results/raw/code_profile_scaling.csv`
- `python scripts/summarize_results.py`
  - Result: completed and wrote/updated summary CSV files
- `python scripts/plot_round2_results.py`
  - Result: completed and wrote Round 2 diagnostic PNG/PDF figures

## Result Notes

- `cache_aware.csv` has 972 rows and all rows report `correctness_passed=True`.
- `code_profile_scaling.csv` has 48 rows and all rows report
  `correctness_passed=True`.
- Current `PackedBlockLUT.apply_many_packed` still uses Python-side mask
  extraction per sample/block; the benchmark is diagnostic, not a speedup
  claim.
- Synthetic code profiles are marked as synthetic. Candidate profiles are
  benchmark workloads, not official standard claims.

## Not Done

- No candidate-testing benchmark.
- No optical-FEC-like workload trace.
- No product-like, staircase-like, or oFEC-like workload.
- No full publication-figure v2 refactor.
- No full preset run.
- No paper text or paper conclusion.
- No BER simulation.
- No complete OFEC decoder.
- No complete BCH algebraic decoder.
- No external code copied.
