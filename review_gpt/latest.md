# Latest Review Summary

Current round: Round 33.

Review bundle path:

- `round33_review_bundle.zip`

## Scope

Round 33 is limited to the fixed-width Fig. 3 diagnostic requested for
`PackedBlockLUTKernel` at block width `w=14`. It does not touch Fig. 2, Fig. 4,
OFEC simulation code, or decoder/BER artifacts.

The measured task is the same fixed GF(2) linear map in each comparison:

- syndrome: `v H^T` for BCH(255,239), r16
- parity: `u P` for BCH(255,239), r16

The plotted baseline is `PackedBatchGF2Kernel.apply_many`, labelled in figures
as `direct vectorized GF(2) matmul`. The measured LUT backend is
`PackedBlockLUTKernel.apply_many_packed`, labelled as `block-LUT (w=14)`.

## Added Files

Benchmark:

- `benchmarks/bench_round33_fig3_dense_batch.py`

Plot and summary script:

- `scripts/plot_round33_fig3_dense_batch.py`

Test:

- `tests/test_round33_fig3.py`

## Raw Data

Merged CSVs:

- `results/raw/round33_fig3_throughput_all.csv`
- `results/raw/round33_fig3_stage_breakdown_all.csv`
- `results/raw/round33_fig3_throughput_summary.csv`
- `results/raw/round33_fig3_speedup_summary.csv`

Worker/source CSVs:

- `results/raw/round33_worker_e_throughput.csv`
- `results/raw/round33_worker_g_throughput.csv`
- `results/raw/round33_worker_d_stage.csv`
- `results/raw/round33_worker_d_stage_throughput.csv`

The original full three-round throughput shards A/B/C were stopped before the
1-hour per-process limit after roughly 53 minutes because they had not reached
the final CSV write. Fallback worker E completed batch sizes `10` through
`100000` with two rounds, `repeats=15`, and `warmups=10`. Worker G completed
batch `300000` with one round, `repeats=15`, and `warmups=2`. Worker D completed
the stage diagnostic for all requested dense batch sizes, including `1000000`
and `3000000`.

Throughput for `1000000` and `3000000` is not reported in this round. Those
long-stream points exceeded the practical budget with the current end-write CSV
runner. The stage diagnostic still covers those sizes.

## Figures

Generated from the merged CSVs:

- `results/figures/round33_fig3_dense_batch.png`
- `results/figures/round33_fig3_dense_batch.pdf`
- `results/figures/round33_fig3_dense_batch_median.png`
- `results/figures/round33_fig3_dense_batch_median.pdf`
- `results/figures/round33_fig3_dense_batch_envelope.png`
- `results/figures/round33_fig3_dense_batch_envelope.pdf`
- `results/figures/round33_fig3_scatter.png`
- `results/figures/round33_fig3_scatter.pdf`
- `results/figures/round33_fig3_stage_breakdown.png`
- `results/figures/round33_fig3_stage_breakdown.pdf`

The paper-facing primary file is the min-view plot
`round33_fig3_dense_batch.*`; the median, max-envelope, scatter, and stage plots
are review diagnostics.

## Correctness Gate

All timed throughput rows passed the exactness check against `NaiveGF2Kernel`:

- throughput rows: 248 timed rows, 248 correctness-passed rows
- stage rows: 72 rows, all correctness-passed

No speed number in the Round33 CSV is reported for a row that failed exactness.

## Main Throughput Observations

Bulk mode, median throughput:

| task | best LUT batch | LUT Mbit/s | direct Mbit/s | LUT/direct at best LUT | best ratio batch | best LUT/direct |
|---|---:|---:|---:|---:|---:|---:|
| syndrome | 2000 | 517.230 | 18.065 | 28.632 | 700 | 30.517 |
| parity | 2000 | 570.438 | 17.176 | 33.210 | 1500 | 34.186 |

Fixed-chunk streaming mode with `chunk_size=1000`, median throughput:

| task | batch | LUT Mbit/s | direct Mbit/s | LUT/direct |
|---|---:|---:|---:|---:|
| syndrome | 100000 | 234.243 | 17.293 | 13.546 |
| syndrome | 300000 | 486.455 | 35.539 | 13.688 |
| parity | 100000 | 253.327 | 17.354 | 14.598 |
| parity | 300000 | 506.370 | 35.772 | 14.155 |

The `300000` rows are single-round rows, so their CV is blank. They are useful
as a long-stream extension, but the two-round `100000` rows are the safer
stability reference.

## Batch-1000 / L1-Fit Diagnosis

The data does not support a narrow claim that a true throughput peak occurs
exactly at batch `1000` because of L1 input fit.

Evidence:

- syndrome bulk LUT throughput is a plateau from roughly batch `700` to `2000`,
  with the measured maximum at `2000`, not `1000`.
- parity bulk LUT throughput also reaches its measured maximum at `2000`.
- batch `1000` has active input around 31 KiB for syndrome and 29 KiB for
  parity, close to a nominal 32 KiB L1D size, but batch `1500` and `2000` are
  already above that active-input footprint and remain as fast or faster.
- stage timing is dominated by index calculation across the range. Around
  batch `1000` to `2000`, index share stays around 68-70 percent, read/prepare
  around 21-24 percent, lookup around 5-6 percent, with no isolated L1-edge
  transition.

Conservative interpretation: the current data supports a small/mid-batch
throughput plateau and a later drop after roughly `2000` to `3000` codewords.
It does not justify a stronger "batch 1000 is the true L1-fit peak" claim.

## Budget Notes

The over-heavy original shard configuration was:

- all 18 requested batch sizes
- syndrome and parity
- bulk and fixed-chunk streaming
- two backends
- three rounds per worker
- `repeats=15`, `warmups=30`

That configuration did not finish a worker CSV before the 1-hour per-process
limit. The fallback configuration kept `repeats=15` and the dense small/mid
batch grid, reduced rounds and warmups, and added a single `300000` long-stream
extension.

## Verification

Commands run:

- `python -B -m pytest tests/test_round33_fig3.py -q`
- `python -B -m pytest tests -q`

Results:

- Round33 test: 4 passed
- full suite: 322 passed, 1 skipped

## Push Status

The Round33 commit was created locally and pushed after transient GitHub
connectivity failures:

- attempt 1: `Could not resolve host: github.com`
- attempt 2: `Recv failure: Connection was reset`
- attempt 3: push succeeded
