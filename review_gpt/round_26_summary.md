# Round 26 Summary: Fixed-Map Three-Backend And Cache-Width Benchmarks

## Scope

This round added three benchmark entry points and one smoke-test file:

- `benchmarks/bench_fixed_map_three_backend.py`
- `benchmarks/bench_block_width_cache_sweep.py`
- `benchmarks/bench_decode_syndrome_accel.py`
- `tests/test_fixed_map_experiment_benchmarks.py`

The round also generated:

- `results/raw/fixed_map_three_backend.csv`
- `results/raw/block_width_cache_sweep.csv`
- `results/raw/decode_syndrome_accel.csv`
- `results/raw/candidate_testing.csv`

Review bundle:

- `round26_fixed_map_review_bundle.zip`

No existing kernel was refactored.

## External Convention Check

The owner-provided OFEC reference files were inspected read-only:

- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_backends.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_lut.py`

The reference constructs column syndromes by one-hot
`galois.BCH(n,k).encode()` for the first `k` information positions and unit
columns for the final parity positions. This is the same `H^T=[P;I]`,
`parity=first k rows` convention used by
`make_bch255_t2_syndrome_matrix_galois_systematic()`. No matrix-source update
was needed.

The reference fast decoder uses a syndrome-to-position LUT for zero, one, and
two bit errors. It was not copied.

## Exp 1 Data

`bench_fixed_map_three_backend.py` compares:

- `galois_per_codeword`: naive per-codeword library-call baseline;
- `PackedBatchGF2Kernel.apply_many`: fair whole-matrix NumPy/PackedBatch
  baseline;
- `PackedBlockLUTKernel.apply_many_packed`: block-LUT kernel using the selected
  block width from Exp 2.

Profiles:

- `bch_255_239_r16`
- `bch_511_484_r27`

Output:

- `results/raw/fixed_map_three_backend.csv`
- 96 rows
- all `correctness_passed=True`
- 32 rows have `timed=False` due to the timing-budget guard

Selected LUT block widths:

| Profile | Task | Selected a | Cache fit from Exp 2 |
|---|---|---:|---|
| `bch_255_239_r16` | parity | 13 | L2 |
| `bch_255_239_r16` | syndrome | 12 | L2 |
| `bch_511_484_r27` | parity | 18 | DRAM |
| `bch_511_484_r27` | syndrome | 20 | DRAM |

LUT ratio ranges versus fair whole-matrix NumPy/PackedBatch over timed rows:

- `bch_255_239_r16` parity: 0.263x to 16.279x
- `bch_255_239_r16` syndrome: 0.230x to 10.157x
- `bch_511_484_r27` parity: 0.193x to 28.288x
- `bch_511_484_r27` syndrome: 0.500x to 21.936x

LUT ratio ranges versus per-codeword galois over timed galois rows:

- `bch_255_239_r16` parity: 2.350x to 255.914x
- `bch_255_239_r16` syndrome: 1.226x to 51.204x
- `bch_511_484_r27` parity: 0.958x to 132.661x
- `bch_511_484_r27` syndrome: 1.058x to 44.239x

The two ratio families should not be merged. The PackedBatch comparison is the
fair same-task vectorized comparison; the galois comparison is the
per-codeword library-call comparison.

## Exp 2 Data

`bench_block_width_cache_sweep.py` scans block widths:

- `8, 10, 11, 12, 13, 14, 16, 18, 20`

Batch sizes in the CSV:

- `100, 1000, 10000, 100000, 1000000, 10000000`

Output:

- `results/raw/block_width_cache_sweep.csv`
- 264 rows
- all `correctness_passed=True`
- 96 rows have `timed=False` due to timing-budget guards

Best measured LUT block widths among timed rows:

| Profile | Task | Batch | Best a | Cache fit | vs PackedBatch | vs galois |
|---|---|---:|---:|---|---:|---:|
| `bch_255_239_r16` | parity | 100 | 18 | L3 | 5.711x | 258.142x |
| `bch_255_239_r16` | parity | 1000 | 14 | L2 | 11.878x | 269.846x |
| `bch_255_239_r16` | parity | 10000 | 11 | L2 | 7.270x | NA |
| `bch_255_239_r16` | parity | 100000 | 13 | L2 | 4.969x | NA |
| `bch_255_239_r16` | syndrome | 100 | 14 | L2 | 13.926x | 113.058x |
| `bch_255_239_r16` | syndrome | 1000 | 14 | L2 | 9.922x | 102.395x |
| `bch_255_239_r16` | syndrome | 10000 | 11 | L2 | 6.596x | NA |
| `bch_255_239_r16` | syndrome | 100000 | 12 | L2 | 4.969x | NA |
| `bch_511_484_r27` | parity | 100 | 18 | DRAM | 19.358x | 60.919x |
| `bch_511_484_r27` | parity | 1000 | 12 | L2 | 19.544x | 92.935x |
| `bch_511_484_r27` | parity | 10000 | 13 | L3 | 18.929x | NA |
| `bch_511_484_r27` | parity | 100000 | 18 | DRAM | 9.835x | NA |
| `bch_511_484_r27` | syndrome | 100 | 16 | L3 | 13.514x | 26.945x |
| `bch_511_484_r27` | syndrome | 1000 | 12 | L2 | 25.199x | 77.630x |
| `bch_511_484_r27` | syndrome | 10000 | 10 | L2 | 18.931x | NA |
| `bch_511_484_r27` | syndrome | 100000 | 20 | DRAM | 8.080x | NA |

The CSV records the theoretical `a=32` footprint for each row. It is classified
as DRAM for all rows in this run.

## Decode Syndrome Backend Swap

`bench_decode_syndrome_accel.py` uses the same `BDDLUTDecoder` object and swaps
only the syndrome backend:

- reference: `NaiveGF2Kernel.apply_many`
- tested: `PackedBlockLUTKernel.apply_many_packed`

Output:

- `results/raw/decode_syndrome_accel.csv`
- 16 rows
- all `correctness_passed=True`
- all decision, status, and corrected-word mismatch counts are `0`

The error locator is the decoder's syndrome-to-position LUT; no BM/Chien or
new locator path was added.

Wall-clock ratios `Naive median / LUT median`:

- `bch_255_239_r16`: 1.830x to 3.703x
- `bch_511_484_r27`: 2.616x to 6.222x

## Candidate Syndrome Extension

The existing `bench_candidate_testing.py` was run for one BCH(255,239)
fixed-weight candidate-syndrome batch:

- candidate weight: 2
- candidate count: 4096
- block width: 12
- repeats: 9

Output:

- `results/raw/candidate_testing.csv`
- 7 rows
- all `correctness_passed=True`

For this batch, `PackedBlockLUT.apply_many_packed` throughput is 11.833x
`PackedBatch.apply_many` throughput. This is a supporting kernel data point
only.

## Timing Budget

Full benchmark wall-clock measurements:

- block-width/cache sweep: about 916 s
- three-backend benchmark: about 296 s
- decode syndrome-backend swap: about 88 s
- candidate syndrome run: about 5.5 s

Maximum timed batch size used for Exp 1 and Exp 2 was `100000`. Larger
configured rows are present but untimed. They should not be used as throughput
data.

Under the current single-thread harness and machine, a full multi-profile
block-width sweep to batch `100000` fits within a 30 minute wall-clock budget.

## Verification Status

Completed before this summary was written:

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
- No OFEC/staircase outer loop.
- No existing kernel refactor.
- No eBCH(256,239) in the new Exp 1/Exp 2 outputs.
- Use only rows with `correctness_passed=True` and `timed=True` for throughput
  ratios.
