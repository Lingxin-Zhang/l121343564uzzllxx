# Latest Review Summary

Current round: Round 26 fixed-map three-backend comparison and block-width/cache sweep.

## Goal

Add benchmark-only artifacts for fixed GF(2) linear maps:

- Exp 1 data: `results/raw/fixed_map_three_backend.csv`
- Exp 2 data: `results/raw/block_width_cache_sweep.csv`
- Decode syndrome-backend swap data: `results/raw/decode_syndrome_accel.csv`
- Candidate syndrome extension data: `results/raw/candidate_testing.csv`

This round does not refactor existing kernels and does not add BER simulation or
an OFEC/staircase outer loop.

Review bundle path:

- `round26_fixed_map_review_bundle.zip`

## Files Added Or Updated

Added:

- `benchmarks/bench_fixed_map_three_backend.py`
- `benchmarks/bench_block_width_cache_sweep.py`
- `benchmarks/bench_decode_syndrome_accel.py`
- `tests/test_fixed_map_experiment_benchmarks.py`
- `results/raw/fixed_map_three_backend.csv`
- `results/raw/block_width_cache_sweep.csv`
- `results/raw/decode_syndrome_accel.csv`
- `review_gpt/round_26_summary.md`
- `round26_fixed_map_review_bundle.zip`

Updated:

- `results/raw/candidate_testing.csv`
- `review_gpt/latest.md`

Pre-existing uncommitted local files were left unstaged.

## Step 0: External Reference Convention Check

Read-only reference files inspected:

- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_backends.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_lut.py`

Observed convention in the reference:

- `build_galois_reference(n_bch, k)` constructs one `galois.BCH(n_bch, k)`.
- `_build_column_syndromes()` one-hot encodes each information bit.
- For information positions `0..k-1`, the column syndrome is the parity suffix
  `codeword[k:]`.
- For parity positions `k..n-1`, the column syndrome is the corresponding unit
  vector bit.
- Therefore the reference matrix convention is `H^T = [P; I]`, with
  `parity = u P` from the first `k` rows.
- Error location in the reference fast backend is syndrome-to-position LUT over
  all zero, one-error, and two-error patterns. It is not an online BM/Chien
  path.

Local check:

- `codes/bch_like.py::make_bch255_t2_syndrome_matrix_galois_systematic()`
  builds `P` by one-hot `galois.BCH(255,239).encode()` and appends
  `I_16`.
- The local convention matches the reference convention above for
  `H^T=[P;I]` and `parity=first k rows`.
- No matrix-source code update was made.
- The reference `SyndromeLUTBCHBackend` was not copied; this round only reused
  the convention.

## Exp 2: Block Width And Cache Sweep

Command:

```bash
python -B -m benchmarks.bench_block_width_cache_sweep --batch-sizes 100,1000,10000,100000,1000000,10000000 --block-widths 8,10,11,12,13,14,16,18,20 --repeats 9 --warmups 2 --max-in-memory-rows 100000 --max-timed-batch-size 100000 --max-galois-batch-size 1000
```

Output:

- `results/raw/block_width_cache_sweep.csv`
- 264 rows
- all rows have `correctness_passed=True`
- 96 rows have `timed=False` because they exceeded the configured timing
  budget guard; no throughput number was filled for those rows.
- Total command wall-clock: about 916 s.

Best measured LUT block width by `(profile, task, batch)` among timed rows:

| Profile | Task | Batch | Best a | Cache fit | LUT Mbit/s | vs PackedBatch | vs galois |
|---|---:|---:|---:|---|---:|---:|---:|
| `bch_255_239_r16` | parity | 100 | 18 | L3 | 410.653 | 5.711x | 258.142x |
| `bch_255_239_r16` | parity | 1000 | 14 | L2 | 660.951 | 11.878x | 269.846x |
| `bch_255_239_r16` | parity | 10000 | 11 | L2 | 384.628 | 7.270x | NA |
| `bch_255_239_r16` | parity | 100000 | 13 | L2 | 207.077 | 4.969x | NA |
| `bch_255_239_r16` | syndrome | 100 | 14 | L2 | 331.169 | 13.926x | 113.058x |
| `bch_255_239_r16` | syndrome | 1000 | 14 | L2 | 521.899 | 9.922x | 102.395x |
| `bch_255_239_r16` | syndrome | 10000 | 11 | L2 | 334.233 | 6.596x | NA |
| `bch_255_239_r16` | syndrome | 100000 | 12 | L2 | 208.421 | 4.969x | NA |
| `bch_511_484_r27` | parity | 100 | 18 | DRAM | 403.670 | 19.358x | 60.919x |
| `bch_511_484_r27` | parity | 1000 | 12 | L2 | 540.782 | 19.544x | 92.935x |
| `bch_511_484_r27` | parity | 10000 | 13 | L3 | 411.624 | 18.929x | NA |
| `bch_511_484_r27` | parity | 100000 | 18 | DRAM | 221.643 | 9.835x | NA |
| `bch_511_484_r27` | syndrome | 100 | 16 | L3 | 300.412 | 13.514x | 26.945x |
| `bch_511_484_r27` | syndrome | 1000 | 12 | L2 | 562.713 | 25.199x | 77.630x |
| `bch_511_484_r27` | syndrome | 10000 | 10 | L2 | 399.247 | 18.931x | NA |
| `bch_511_484_r27` | syndrome | 100000 | 20 | DRAM | 174.894 | 8.080x | NA |

Rows for batch `1000000` and `10000000` are present but untimed in this run.
The CSV records `theoretical_a32_lut_table_bytes` and
`theoretical_a32_cache_level_fit=DRAM` for every row.

## Exp 1: Three Backend Fixed-Map Comparison

Command:

```bash
python -B -m benchmarks.bench_fixed_map_three_backend --batch-sizes 1,10,100,1000,10000,100000,1000000 --long-batch-sizes 5000000 --repeats 9 --warmups 2 --selection-batch-size 100000 --max-in-memory-rows 100000 --max-timed-batch-size 100000 --max-galois-batch-size 1000
```

Output:

- `results/raw/fixed_map_three_backend.csv`
- 96 rows
- all rows have `correctness_passed=True`
- 32 rows have `timed=False` because they exceeded the configured timing
  budget guard.
- Total command wall-clock: about 296 s.

The LUT block widths were selected from Exp 2 at batch `100000`:

| Profile | Task | Selected a | Cache fit in Exp 2 |
|---|---|---:|---|
| `bch_255_239_r16` | parity | 13 | L2 |
| `bch_255_239_r16` | syndrome | 12 | L2 |
| `bch_511_484_r27` | parity | 18 | DRAM |
| `bch_511_484_r27` | syndrome | 20 | DRAM |

Measured LUT ratios versus the fair whole-matrix NumPy/PackedBatch baseline:

- `bch_255_239_r16` parity: 0.263x to 16.279x over timed batches.
- `bch_255_239_r16` syndrome: 0.230x to 10.157x over timed batches.
- `bch_511_484_r27` parity: 0.193x to 28.288x over timed batches.
- `bch_511_484_r27` syndrome: 0.500x to 21.936x over timed batches.

Measured LUT ratios versus the per-codeword galois baseline:

- `bch_255_239_r16` parity: 2.350x to 255.914x for timed galois rows.
- `bch_255_239_r16` syndrome: 1.226x to 51.204x for timed galois rows.
- `bch_511_484_r27` parity: 0.958x to 132.661x for timed galois rows.
- `bch_511_484_r27` syndrome: 1.058x to 44.239x for timed galois rows.

These are two separate comparisons. The PackedBatch comparison is the fair
same-task vectorized baseline. The galois comparison is the naive per-codeword
library-call baseline and is not the headline baseline.

## Timing Budget Notes

Maximum observed per-configuration timing among timed rows:

| Benchmark | Batch | Timed rows | Max median runtime (s) | Max config elapsed (s) |
|---|---:|---:|---:|---:|
| block-width sweep | 100 | 44 | 0.015024 | 0.161557 |
| block-width sweep | 1000 | 44 | 0.097576 | 1.156640 |
| block-width sweep | 10000 | 40 | 0.242304 | 3.043200 |
| block-width sweep | 100000 | 40 | 2.360830 | 30.979600 |
| three-backend | 1 | 12 | 0.000276 | 0.003842 |
| three-backend | 10 | 12 | 0.001955 | 0.022915 |
| three-backend | 100 | 12 | 0.008579 | 0.122528 |
| three-backend | 1000 | 12 | 0.107228 | 1.341490 |
| three-backend | 10000 | 8 | 0.206756 | 2.588650 |
| three-backend | 100000 | 8 | 2.302880 | 28.165800 |

With this harness and machine, the full single-thread multi-profile
block-width sweep fits batch `100000` within a 30 minute wall-clock budget. The
configured `1000000`, `5000000`, and `10000000` rows were retained as budget
guard rows but not timed; they must not be used as throughput data.

## Decode Syndrome Backend Swap

Command:

```bash
python -B -m benchmarks.bench_decode_syndrome_accel --batch-sizes 100,1000,10000,100000 --repeats 9 --warmups 2 --block-width 12 --t 2 --max-in-memory-rows 100000
```

Output:

- `results/raw/decode_syndrome_accel.csv`
- 16 rows
- all rows have `correctness_passed=True`
- all decision, status, and corrected-word mismatch counts are `0`
- Total command wall-clock: about 88 s.

Error location is `BDDLUTDecoder`'s syndrome-to-position LUT for zero, one, and
two bit errors. The benchmark only changes the syndrome linear-map backend:

- reference syndrome backend: `NaiveGF2Kernel.apply_many`
- tested syndrome backend: `PackedBlockLUTKernel.apply_many_packed`

Measured wall-clock ratios `Naive median / LUT median`:

- `bch_255_239_r16`: 1.830x to 3.703x over batches `100..100000`
- `bch_511_484_r27`: 2.616x to 6.222x over batches `100..100000`

## Candidate Syndrome Extension

Command:

```bash
python -B -m benchmarks.bench_candidate_testing --preset lightweight --repeats 9 --code-profiles bch_255_239_r16 --pattern-types fixed_weight --candidate-weights 2 --candidate-counts 4096 --block-width 12 --target-mode known_hit
```

Output:

- `results/raw/candidate_testing.csv`
- 7 rows
- all rows have `correctness_passed=True`

For this candidate-syndrome batch, `PackedBlockLUT.apply_many_packed` throughput
was 11.833x the `PackedBatch.apply_many` throughput. This is recorded only as a
kernel-extension data point, not as a main-figure result.

## Verification

Commands run so far:

```bash
python -B -m pytest tests/test_fixed_map_experiment_benchmarks.py -q
python -B -m benchmarks.bench_block_width_cache_sweep --batch-sizes 100,1000,10000,100000,1000000,10000000 --block-widths 8,10,11,12,13,14,16,18,20 --repeats 9 --warmups 2 --max-in-memory-rows 100000 --max-timed-batch-size 100000 --max-galois-batch-size 1000
python -B -m benchmarks.bench_fixed_map_three_backend --batch-sizes 1,10,100,1000,10000,100000,1000000 --long-batch-sizes 5000000 --repeats 9 --warmups 2 --selection-batch-size 100000 --max-in-memory-rows 100000 --max-timed-batch-size 100000 --max-galois-batch-size 1000
python -B -m benchmarks.bench_decode_syndrome_accel --batch-sizes 100,1000,10000,100000 --repeats 9 --warmups 2 --block-width 12 --t 2 --max-in-memory-rows 100000
python -B -m benchmarks.bench_candidate_testing --preset lightweight --repeats 9 --code-profiles bch_255_239_r16 --pattern-types fixed_weight --candidate-weights 2 --candidate-counts 4096 --block-width 12 --target-mode known_hit
```

Fresh full-suite pytest result:

```bash
python -B -m pytest
```

- `303 passed, 1 skipped, 27 warnings`

## Boundaries

- No BER simulation.
- No full OFEC/staircase decoder.
- No existing kernel refactor.
- No eBCH(256,239) profile in the new Exp 1/Exp 2 benchmark outputs.
- Ratios above are tied only to rows with `correctness_passed=True` and
  `timed=True`.
