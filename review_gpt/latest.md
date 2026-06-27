# Latest Review Summary

Current round: Round 28 M2 minimal end-to-end product-code BER simulator.

## Goal

Build a new minimal end-to-end simulator outside the GF(2) kernel repository
and verify that replacing only the component syndrome backend with block-LUT
does not change the resulting BER-vs-SNR curve.

Review bundle path:

- `round28_m2_ofec_sim_review_bundle.zip`

## Boundary

The new simulator lives in the sibling directory:

- `D:\PKU\acp2026\m2_ofec_sim`

This follows `fec_linear_backend/AGENTS.md`: BER simulation and full decoder
runs are not added to the GF(2) kernel repository. The review bundle checked
into this repository contains the M2 source and generated CSVs for review.

## Local OFEC Study

Files read:

- `D:\PKU\OFEC\project\ofec-0.1.0\scripts\reproduce_fig3_baseline.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\*.py`
- `D:\PKU\OFEC\project\ofec-huawei-github\HUAWEI-OFEC-Tao\...`

Key points:

- `h` is the number of hard-decision decoder stages. The local decoder window
  size is derived as `10*h + 1` blocks.
- `min_post_errors` stops one SNR point after enough post-FEC bit errors have
  accumulated.
- `max_blocks` is the per-SNR safety cap.
- `batch_blocks` controls how many output blocks are generated and pushed
  through the channel/decoder per outer loop batch.
- The local script counts only emitted measurement-phase blocks after decoder
  warmup/window latency.
- Local `ofec-0.1.0` reaches low BER quickly because it has a batched
  Python/NumPy path, a dense syndrome-LUT EBCH backend, windowed streaming
  measurement, and optional parallel modes.
- The Huawei reference tree is a compiled AFF3CT-style C++ implementation with
  templated encoder/decoder modules and performance-oriented monitor/decoder
  structure; it is not copied here.

## M2 Structure

M2 source files in the bundle:

- `m2_ofec_sim/AGENTS.md`
- `m2_ofec_sim/m2_ofec_sim/channel.py`
- `m2_ofec_sim/m2_ofec_sim/cli.py`
- `m2_ofec_sim/m2_ofec_sim/paths.py`
- `m2_ofec_sim/m2_ofec_sim/product_code.py`
- `m2_ofec_sim/m2_ofec_sim/sim.py`
- `m2_ofec_sim/tests/test_m2_end_to_end.py`

The simulator implements:

- component code: BCH(255,239), using
  `make_bch255_t2_syndrome_matrix_galois_systematic()`
- product-code block: `255 x 255`, built by row parity then column parity
- channel: normalized 16-QAM AWGN hard decision, with padding removed after
  demodulation
- decoder: `h` row/column BDD sweeps
- locator: shared `BDDLUTDecoder` syndrome-to-position table for t<=2
- reference syndrome backend: `PackedBatchGF2Kernel.apply_many`
- accelerated syndrome backend: `PackedBlockLUTKernel.apply_many_packed`,
  `block_width=14`

Only the syndrome linear map backend changes. The BDD locator and correction
logic are shared between the two curves.

## Run

Command:

```bash
python -B -m m2_ofec_sim.cli --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 10 --batch-blocks 1 --seed 42 --block-width 14 --time-budget-s 1800 --output-dir results/raw
```

Raw CSVs in the bundle:

- `m2_ofec_sim/results/raw/m2_reference_ber.csv`
- `m2_ofec_sim/results/raw/m2_block_lut_ber.csv`
- `m2_ofec_sim/results/raw/m2_curve_diff.csv`
- `m2_ofec_sim/results/raw/m2_timing.csv`

## BER Equality

All six SNR points matched exactly:

- SNR: `13.7, 13.8, 13.9, 14.0, 14.1, 14.2`
- `blocks_delta = 0`
- `total_bits_delta = 0`
- `pre_errors_delta = 0`
- `post_errors_delta = 0`
- `pre_ber_delta = 0.0`
- `post_ber_delta = 0.0`

This is the end-to-end result for M2: same seed, same channel draws, same
product-code iterative decoder, same locator, and identical BER outputs after
only replacing the syndrome backend.

## Timing

From `m2_timing.csv`:

- reference total elapsed: `2.9768890000414103 s`
- block-LUT total elapsed: `2.782408499857411 s`
- total ratio, reference/block-LUT: `1.0698964584797546x`
- reference online elapsed: `0.3521323000313714 s`
- block-LUT online elapsed: `0.15540809993399307 s`
- online ratio, reference/block-LUT: `2.265858`

The one-time matrix/table initialization dominates this smoke run. The online
row/column decoding portion is where the block-LUT backend is visibly faster.

## Per-SNR Results

Post-FEC BER values are read from the CSV:

| SNR dB | blocks | post errors | post BER |
|---:|---:|---:|---:|
| 13.7 | 1 | 819 | 0.01259515570934256 |
| 13.8 | 1 | 541 | 0.008319876970396002 |
| 13.9 | 1 | 437 | 0.006720492118415994 |
| 14.0 | 1 | 278 | 0.004275278738946559 |
| 14.1 | 1 | 336 | 0.00516724336793541 |
| 14.2 | 3 | 145 | 0.0007433038574907087 |

This is a short smoke/demo BER curve, not a low-floor production run.

## Budget Note

The run completed well inside the 30 minute budget; no timeout stop occurred.

Observed online time per product-code block:

- reference: `0.04401653750392143 s/block`
- block-LUT: `0.019426012491749134 s/block`

For a simple counting estimate of 100 post errors at a target BER over 65025
bits/block, the observed online throughput implies:

| target BER | blocks | reference online | block-LUT online |
|---:|---:|---:|---:|
| 1e-6 | 1538 | 1.1283 min | 0.4980 min |
| 1e-7 | 15379 | 11.2822 min | 4.9792 min |
| 1e-8 | 153788 | 112.8203 min | 49.7915 min |

This is only a throughput-based estimate for future planning, not a claim that
the current high-SNR M2 channel reaches those floors in this round.

## Not Done

- No long BER floor run.
- No 1e-8 claim.
- No end-to-end OFEC/staircase replacement of local `ofec-0.1.0`.
- No changes to existing GF(2) kernels.

## Verification

Commands run:

```bash
python -B -m pytest tests -q
python -B -m m2_ofec_sim.cli --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 10 --batch-blocks 1 --seed 42 --block-width 14 --time-budget-s 1800 --output-dir results/raw
python -B -m pytest
```

Results:

- M2 smoke test: `1 passed`
- BER sweep: `points=6 matched=True reference_over_block_lut=1.0699`
- `fec_linear_backend` full test suite: `306 passed, 1 skipped, 27 warnings`
