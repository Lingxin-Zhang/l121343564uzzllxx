# Latest Review Summary

Current round: Round 10 - BCH-like Component Syndrome Kernel

## Modified Files

- `.gitignore`
- `AGENTS.local.md.example`
- `README.md`
- `codes/__init__.py`
- `codes/bch_like.py`
- `tests/test_bch_like.py`
- `benchmarks/bench_bch_syndrome.py`
- `scripts/run_all_benchmarks.py`
- `scripts/plot_results.py`
- `results/raw/*.csv`
- `results/figures/*.png`

## Implementation

- Added `codes/bch_like.py`, a clean public reimplementation that generates a
  deterministic `(255, 16)` BCH-like component syndrome matrix.
- Added `BCH255_T2_SYNDROME_SPEC` metadata and exports from `codes/__init__.py`.
- The configured local external reference path was accessible in this
  environment, but no external code was copied into this repository.
- Current BCH-like matrix is a deterministic reimplemented component-kernel
  placeholder, not yet verified against OFEC_CNN.
- Allowed `codes/bch_like.py` to be tracked while keeping `codes/ebch_like.py`,
  `paper/`, and `references/` ignored.
- Replaced the concrete local path in `AGENTS.local.md.example` with a generic
  placeholder path.
- Added `benchmarks/bench_bch_syndrome.py` for the component syndrome workload.
- Added `bch_syndrome_throughput.png` generation in `scripts/plot_results.py`.
- Added the new benchmark to `scripts/run_all_benchmarks.py`.

## Correctness Tests

```text
python -m pytest -q
164 passed
```

The new tests check:

- syndrome matrix shape, dtype, bit values, and determinism;
- zero input gives zero syndrome;
- `NaiveGF2Kernel`, `PackedBatchGF2Kernel`, `PackedBlockLUT.apply_many`, and
  `PackedBlockLUT.apply_many_packed` agree for batch sizes `1`, `64`, and
  `4096` at densities `0.005`, `0.05`, and `0.5`.

## Benchmark / Figures

```text
python scripts/run_all_benchmarks.py
```

Generated CSV files:

- `results/raw/block_width.csv`
- `results/raw/density.csv`
- `results/raw/batch.csv`
- `results/raw/stream.csv`
- `results/raw/bch_syndrome.csv`

Generated PNG figures:

- `results/figures/block_width_vs_latency.png`
- `results/figures/block_width_table_size.png`
- `results/figures/density_backend_comparison.png`
- `results/figures/batch_crossover.png`
- `results/figures/stream_throughput.png`
- `results/figures/bch_syndrome_throughput.png`

For `bch_syndrome.csv` in this run, average throughput by backend was:

- `Naive.apply_many`: about `44.02` Mbit/s
- `PackedBatch.apply_many`: about `43.89` Mbit/s
- `PackedBlockLUT.apply_many`: about `511.65` Mbit/s
- `PackedBlockLUT.apply_many_packed`: about `500.15` Mbit/s

The fastest backend by this simple average was `PackedBlockLUT.apply_many`.
This is a benchmark observation from the generated CSV, not a paper conclusion.

`PackedBlockLUT.apply_many_packed` returns one `uint16` per word and skips
unpacking to a `(batch, r)` bit matrix. `PackedBlockLUT.apply_many` calls the
packed path and then unpacks. In this run the two timings were close and not
strictly ordered for every setting, so the difference should be treated as
implementation/measurement behavior rather than a stable claim.

## Known Issues

- The BCH-like matrix has not yet been verified against OFEC_CNN.
- This is not a full BCH/eBCH decoder and does not include algebraic decoding.
- No HybridPlanner, BER simulation, formal benchmark claim, or paper conclusion
  was added.

## Next Step

Add an explicit external-reference verification test only after a public-safe
way to compare against the local reference implementation is available.
