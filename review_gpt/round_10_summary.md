# Round 10 Summary - BCH-like Component Syndrome Kernel

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

- Added a deterministic public BCH-like `(255, 16)` component syndrome matrix.
- Current BCH-like matrix is a deterministic reimplemented component-kernel
  placeholder, not yet verified against OFEC_CNN.
- Confirmed the configured local external reference path was accessible, but no
  external code or concrete local path was committed.
- Added correctness tests comparing the BCH-like workload across existing GF(2)
  kernels.
- Added a component syndrome benchmark and PNG plot.

## Test Result

```text
python -m pytest -q
164 passed
```

## Benchmark Result

```text
python scripts/run_all_benchmarks.py
```

Generated:

- `results/raw/bch_syndrome.csv`
- `results/figures/bch_syndrome_throughput.png`

In the BCH-like component syndrome benchmark, the fastest backend by average
throughput in the generated CSV was `PackedBlockLUT.apply_many`. The packed and
unpacked PackedBlockLUT batch paths were close in this run; `apply_many_packed`
returns `uint16` outputs while `apply_many` additionally unpacks to bit
vectors.

## Known Issues

- The BCH-like matrix is not yet externally verified.
- No full BCH/eBCH decoder, HybridPlanner, BER simulation, benchmark claim, or
  paper conclusion was added.

## Next Step

Add external-reference verification when a public-safe comparison harness is
available.
