# GF(2) Kernel Correctness Repository

This repository contains small GF(2) linear-kernel backends, pytest-based
correctness checks, and reproducible micro-benchmark scripts. The current focus
is correctness, API consistency, and transparent measurement, not benchmark
claims.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Run Tests

```bash
pytest
```

## Run Micro-Benchmarks

```bash
python scripts/run_all_benchmarks.py
```

On systems with `bash`, the shell wrapper is also available:

```bash
bash scripts/run_all_benchmarks.sh
```

The benchmark scripts write CSV files to `results/raw/` and initial figures to
`results/figures/`.

## Implemented Modules

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `EventUpdateKernel`
- `PackedBatchGF2Kernel` correctness-first `apply_many`
- `PackedBlockLUTKernel`

## Benchmark Scripts

- `benchmarks/bench_block_width.py`
- `benchmarks/bench_density.py`
- `benchmarks/bench_batch.py`
- `scripts/plot_results.py`

## Not Yet Implemented

- `HybridPlanner`

Do not report performance improvements unless they come from reproducible
benchmark outputs committed with the relevant code and methodology.
