# Round 25 Summary: Exactness Certificate and Fair Baseline Throughput

## Scope

This round added two benchmark entry points and two smoke tests:

- `benchmarks/bench_exactness_certificate.py`
- `benchmarks/bench_fair_baseline_throughput.py`
- `tests/test_exactness_certificate_benchmark.py`
- `tests/test_fair_baseline_throughput_benchmark.py`

The round did not refactor existing kernels and did not add BER simulation or a
full decoder.

## Exp 0: Bit-Exact Certificate

`bench_exactness_certificate.py` checks both required candidate profiles:

- `bch_255_239_r16`
- `ebch_256_239_r17`

For each profile it checks:

- parity single-bit messages;
- parity random batch;
- syndrome single-bit words;
- syndrome all-double-bit words;
- syndrome random batch;
- BDD-LUT decoder consistency between reference syndrome backend and LUT
  syndrome backends.

Reference backend:

- `NaiveGF2Kernel.apply_many`

Tested backends:

- `BlockLUTKernel.apply_many`
- `PackedBlockLUTKernel.apply_many_packed`

Output:

- `results/raw/exactness_certificate.csv`
- 24 rows
- all `status=PASS`
- all `mismatch_count=0`

Command:

```bash
python -B -m benchmarks.bench_exactness_certificate
```

## Exp 1: Fair Baseline Throughput

`bench_fair_baseline_throughput.py` measures same-task GF(2) linear maps for:

- syndrome: `s = x @ matrix mod 2`;
- parity: `p = u @ P mod 2`.

Profiles:

- `bch_255_239_r16`
- `ebch_256_239_r17`

Batch sizes:

- `1, 10, 100, 1000, 10000, 100000, 1000000`

Backends:

- `NaiveGF2Kernel.apply_many`
  - labeled `vectorization-overhead reference only`;
- `PackedBatchGF2Kernel.apply_many`
  - fair vectorized baseline;
- `galois.GF2_matmul`
  - verified same-task third-party baseline in this run;
- `PackedBlockLUTKernel.apply_many_packed`
  - packed block-LUT kernel under test.

Output:

- `results/raw/fair_baseline_throughput.csv`
- 112 rows
- all `correctness_passed=True`
- absolute throughput fields:
  - `throughput_Mbit_s`
  - `throughput_Mcodeword_s`
- environment fields:
  - CPU model
  - L1/L2/L3 cache bytes
  - Python version
  - NumPy version
  - galois version
  - thread settings

Command:

```bash
python -B -m benchmarks.bench_fair_baseline_throughput --batch-sizes 1,10,100,1000,10000,100000,1000000 --repeats 3 --warmups 1
```

## Crossover Notes From Current CSV

LUT net gain over `PackedBatchGF2Kernel`:

- `bch_255_239_r16` parity: starts at batch `100`.
- `bch_255_239_r16` syndrome: starts at batch `10`.
- `ebch_256_239_r17` parity: starts at batch `100`.
- `ebch_256_239_r17` syndrome: starts at batch `100`.

LUT relative to `galois.GF2_matmul`:

- wins appear at batch `1000` and `10000` for BCH parity, eBCH parity, and
  eBCH syndrome;
- BCH syndrome wins appear at batch `10` and `10000`;
- other batch sizes in this run do not support a broad LUT-over-galois speed
  statement.

These notes distinguish:

- LUT net gain: `PackedBlockLUTKernel.apply_many_packed` versus
  `PackedBatchGF2Kernel.apply_many`;
- vectorization gain: any comparison involving `NaiveGF2Kernel.apply_many`,
  which is not a headline baseline.

## Verification

Commands run:

```bash
python -B -m pytest tests/test_exactness_certificate_benchmark.py tests/test_fair_baseline_throughput_benchmark.py
python -B -m benchmarks.bench_exactness_certificate
python -B -m benchmarks.bench_fair_baseline_throughput --batch-sizes 1,10,100,1000,10000,100000,1000000 --repeats 3 --warmups 1
python -B -m pytest
```

Results:

- new smoke tests: `2 passed`;
- exactness certificate: all 24 rows PASS, all mismatch counts 0;
- fair throughput: all 112 rows `correctness_passed=True`;
- full test suite: `300 passed, 1 skipped, 27 warnings`.

## Boundaries

- No BER simulation.
- No full OFEC/staircase decoder.
- No full iBDD outer-loop implementation.
- No speed statement should be used unless it is tied to the exactness
  certificate and the fair throughput CSV generated in this round.
