# Latest Review Summary

Current round: Round 25 exactness certificate and fair baseline throughput.

## Goal

Add two benchmark entry points without refactoring existing kernels:

1. `benchmarks/bench_exactness_certificate.py`
   - bit-exact certificate for `p = u P` and `s = v H^T`;
   - reference backend is `NaiveGF2Kernel`;
   - tested backends are `BlockLUTKernel` and `PackedBlockLUTKernel`;
   - output is `results/raw/exactness_certificate.csv`.
2. `benchmarks/bench_fair_baseline_throughput.py`
   - same-task throughput benchmark for syndrome and parity;
   - compares Naive, PackedBatch, galois, and PackedBlockLUT under one harness;
   - reports absolute `Mbit/s` and `Mcodeword/s`;
   - output is `results/raw/fair_baseline_throughput.csv`.

This round remains a GF(2) kernel benchmark round. It does not add BER
simulation, a full OFEC decoder, or end-to-end results.

## Skills Used

- `superpowers:test-driven-development`: added smoke tests first and verified
  RED before implementing the benchmark modules.
- `superpowers:verification-before-completion`: used before reporting test and
  benchmark status.

No subagent was used.

## Files Added

- `benchmarks/bench_exactness_certificate.py`
- `benchmarks/bench_fair_baseline_throughput.py`
- `tests/test_exactness_certificate_benchmark.py`
- `tests/test_fair_baseline_throughput_benchmark.py`
- `results/raw/exactness_certificate.csv`
- `results/raw/fair_baseline_throughput.csv`
- `review_gpt/round_25_summary.md`

## Exp 0: Exactness Certificate

Command:

```bash
python -B -m benchmarks.bench_exactness_certificate
```

Result:

- Wrote `results/raw/exactness_certificate.csv`.
- CSV has 24 rows.
- `status=PASS` for all 24 rows.
- Every `mismatch_count` is `0`.
- Coverage includes parity single-bit, parity random batch, syndrome single-bit,
  syndrome all-double-bit, syndrome random batch, and BDD-LUT decoder
  consistency.
- Random coverage used the benchmark default:
  `random_batch_size=65536`, `decoder_random_words=4096`, `density=0.05`.

This exactness pass gates the throughput rows below. No throughput observation
should be used without this CSV.

## Exp 1: Fair Baseline Throughput

Command:

```bash
python -B -m benchmarks.bench_fair_baseline_throughput --batch-sizes 1,10,100,1000,10000,100000,1000000 --repeats 3 --warmups 1
```

Result:

- Wrote `results/raw/fair_baseline_throughput.csv`.
- CSV has 112 rows:
  `2 profiles * 2 tasks * 7 batch sizes * 4 backends`.
- `correctness_passed=True` for all 112 rows.
- Batch sizes covered:
  `1, 10, 100, 1000, 10000, 100000, 1000000`.
- Backends:
  - `NaiveGF2Kernel.apply_many`: labeled
    `vectorization-overhead reference only`;
  - `PackedBatchGF2Kernel.apply_many`: fair vectorized baseline;
  - `galois.GF2_matmul`: third-party verified same-task baseline;
  - `PackedBlockLUTKernel.apply_many_packed`: packed block-LUT kernel under
    test.
- Environment fields recorded in each row: CPU model, L1/L2/L3 cache bytes,
  Python version, NumPy version, galois version, and thread settings.

Observed crossover from this CSV:

| Profile | Task | LUT beats PackedBatch at batch sizes | LUT beats galois at batch sizes |
|---|---|---|---|
| `bch_255_239_r16` | parity | `100, 1000, 10000, 100000, 1000000` | `1000, 10000` |
| `bch_255_239_r16` | syndrome | `10, 100, 1000, 10000, 100000, 1000000` | `10, 10000` |
| `ebch_256_239_r17` | parity | `100, 1000, 10000, 100000, 1000000` | `1000, 10000` |
| `ebch_256_239_r17` | syndrome | `100, 1000, 10000, 100000, 1000000` | `1000, 10000` |

Interpretation boundary:

- LUT net gain over the fair vectorized `PackedBatchGF2Kernel` starts at
  batch `100` for parity, batch `10` for BCH syndrome, and batch `100` for
  eBCH syndrome in this run.
- LUT gain over `galois` is narrow and not stable across the full sweep; it
  appears at batch `1000` and `10000` for three profile/task combinations and
  at batch `10` and `10000` for BCH syndrome.
- Do not describe Naive-relative ratios as headline speedups; Naive is present
  only to quantify vectorization/interpreter overhead.
- Do not generalize the galois comparison beyond the recorded batch/profile/task
  rows.

## Verification

Commands run:

```bash
python -B -m pytest tests/test_exactness_certificate_benchmark.py tests/test_fair_baseline_throughput_benchmark.py
python -B -m benchmarks.bench_exactness_certificate
python -B -m benchmarks.bench_fair_baseline_throughput --batch-sizes 1,10,100,1000,10000,100000,1000000 --repeats 3 --warmups 1
python -B -m pytest
```

Results:

- New smoke tests: `2 passed`.
- Exactness certificate: all 24 rows PASS, all mismatch counts 0.
- Fair throughput CSV: all 112 rows have `correctness_passed=True`.
- Full test suite: `300 passed, 1 skipped, 27 warnings`.

## Claim Boundaries

- This is a kernel exactness and same-task throughput benchmark round.
- No BER simulation was run.
- No full component-code, staircase, OFEC, or iBDD outer-loop decoder was added.
- Any speed statement must be tied to `results/raw/exactness_certificate.csv`
  and `results/raw/fair_baseline_throughput.csv`.
- Distinguish LUT net gain over `PackedBatchGF2Kernel` from vectorization gain
  over `NaiveGF2Kernel`.
