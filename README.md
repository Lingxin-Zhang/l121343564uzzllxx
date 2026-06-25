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

The BCH/component workload benchmarks support named `matrix_source` values:

- `galois_systematic_candidate`: main BCH candidate when `galois` is installed.
- `placeholder`: deterministic BCH-like structured workload retained for
  comparison and history.
- `random_fixed`: deterministic random GF(2) matrix for generic micro-
  benchmarks.

Benchmark terms:

- `apply(x)` processes one component word, such as one 255-bit input vector.
- `apply_many(X)` processes a batch of component words with shape
  `(batch_size, n)`.
- `batch_size` is the number of component words processed in one batch call.
- `total_bits` is the total bit count in a synthetic stream benchmark.
- `num_words = total_bits // component_n` is the number of component words cut
  from the stream.
- `chunk_words` is the number of component words processed per chunk to avoid
  excessive memory use.

For example, `total_bits = 1,000,000` and `component_n = 255` gives
`num_words = 3921`, so the stream input has shape `(3921, 255)`.

## Implemented Modules

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `EventUpdateKernel`
- `PackedBatchGF2Kernel` correctness-first `apply_many`
- `PackedBlockLUTKernel`
- `HybridPlanner` simple rule-based baseline

Current `PackedBlockLUTKernel` support is limited to output width `r <= 16`.
Wider packed outputs will need a later `uint32`/`uint64` or multi-word design.

`EventUpdateKernel` supports both single-word `update()` and batch
`update_many()` for event-driven syndrome updates. `HybridPlanner` is a
reproducible rule-based dispatcher baseline, not an optimal scheduler.

## Benchmark Scripts

- `benchmarks/bench_block_width.py`
- `benchmarks/bench_density.py`
- `benchmarks/bench_batch.py`
- `benchmarks/bench_stream.py`
- `benchmarks/bench_bch_syndrome.py`
- `benchmarks/bench_component_loop.py`
- `benchmarks/bench_event_update.py`
- `benchmarks/bench_planner.py`
- `scripts/plot_results.py`

The first benchmark group uses a fixed random GF(2) matrix. The component
syndrome benchmark uses a deterministic BCH-like `(255, 16)` matrix to exercise
the same kernels on a structured public workload.

The deterministic BCH-like matrix is still kept as a placeholder. The BCH
syndrome and component-loop benchmark path can use the separate
galois-systematic verified-candidate matrix when `galois` is installed.
Benchmark defaults and generated figures are reproducible measurement artifacts;
they are not paper conclusions.

Examples:

```bash
python -m benchmarks.bench_bch_syndrome --matrix-source galois_systematic_candidate
python -m benchmarks.bench_bch_syndrome --matrix-source placeholder
python -m benchmarks.bench_component_loop --matrix-source galois_systematic_candidate
python -m benchmarks.bench_event_update --matrix-source galois_systematic_candidate
python -m benchmarks.bench_planner --matrix-source galois_systematic_candidate
```

`bench_event_update.py` reports from-scratch recomputation, per-word loop
update, and batch `update_many`. `bench_planner.py` measures the simple
rule-based dispatcher on batch-syndrome and event-update workloads.

## Reference Policy

This public repository should only describe generic GF(2) kernel benchmark
work. Local reference implementations may be used only for parameter checks and
component-code calling patterns. Do not copy large code blocks. Reimplement
needed logic here, and mark any reference-derived parameter or calling-pattern
usage as reference-only / reimplemented.

BCH-like reference checks are optional and may depend on local external
repositories or installed packages. External code is used only as behavior
reference, not copied into this repository.

Do not report performance improvements unless they come from reproducible
benchmark outputs committed with the relevant code and methodology.
