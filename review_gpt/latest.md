# Latest Review Summary

Current round: Round 29 real OFEC backend injection.

## Goal

Without modifying `D:\PKU\OFEC\project\ofec-0.1.0`, inject an external
block-LUT BCH component backend into the real local OFEC simulator and verify
that the end-to-end BER-vs-SNR curve matches the official `syndrome_lut`
backend point by point while running faster.

Review bundle path:

- `round29_real_ofec_block_lut_review_bundle.zip`

## Boundary

External backend package:

- `D:\PKU\acp2026\ofec_block_lut_backend`

The OFEC source tree was inspected but not edited. The GF(2) kernel repository
still does not host BER simulation source; this repository only contains the
review summary and review bundle.

## OFEC Protocol Notes

Files inspected:

- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_backends.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\_ebch_lut.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\ofec\codec\ebch.py`
- `D:\PKU\OFEC\project\ofec-0.1.0\scripts\reproduce_fig3_baseline.py`

Confirmed interface:

- `BCHBackend.encode(info)` maps 239 information bits to a 255-bit BCH word.
- `BCHBackend.decode(rx_base)` maps a 255-bit received word to
  `(corrected_word, indicator)`.
- `BCHBackend.encode_many(info_batch)` maps `(batch,239)` to `(batch,255)`.
- `BCHBackend.decode_many(rx_base_batch)` maps `(batch,255)` to
  `(corrected_batch, indicators)`.
- indicator semantics: `-1` failure, `0` no correction, `1/2` one or two BCH
  bit corrections.
- `build_bch_backend()` returns a non-string backend object directly, so
  `EBCH256_239(backend=<object>)` injects the external backend.

Confirmed matrix and locator convention:

- official `_build_column_syndromes()` constructs the first 239 columns by
  one-hot encoding through `galois.BCH(255,239)` and taking the systematic
  parity suffix.
- parity columns are the identity, so the unpacked matrix is `H^T=[P;I]`.
- `column_syndrome_bits` is the unpacked `(255,16)` matrix used by
  `(batch @ column_syndrome_bits) & 1`.
- official correction uses `decode_lut`, `decode_counts`, and
  `decode_positions` for 0/1/2-error patterns.

## Implementation

External files included in the bundle:

- `ofec_block_lut_backend/AGENTS.md`
- `ofec_block_lut_backend/ofec_block_lut_backend/__init__.py`
- `ofec_block_lut_backend/ofec_block_lut_backend/backend.py`
- `ofec_block_lut_backend/ofec_block_lut_backend/run_real_ofec_sweep.py`
- `ofec_block_lut_backend/tests/test_block_lut_backend_equivalence.py`

`BlockLUTBCHBackend` imports OFEC's own `build_syndrome_lut_tables()` and
therefore uses the same `column_syndrome_bits`, packed-bit convention, and
decode arrays as `SyndromeLUTBCHBackend`. It replaces only the online
syndrome/parity linear-map evaluation with:

- `PackedBlockLUTKernel(..., block_width=14, packed_word_bits=16)`

The OFEC encoder, sliding-window decoder, hard-stage schedule, eBCH wrapper,
and error locator are not copied or replaced.

## Bit-Exact Gate

Command:

```bash
python -B -m pytest tests -q
```

Run from:

- `D:\PKU\acp2026\ofec_block_lut_backend`

Result:

- `2 passed, 1 warning`

The tests compare:

- BCH `encode_many`
- BCH `decode_many` on mixed 0/1/2/3+ error cases
- `EBCH256_239(...).encode_many`
- `EBCH256_239(...).decode_many` result fields:
  `word`, `error_location`, `status`, `bch_error_indicator`,
  `parity_flip`, and `total_error_estimate`

## Real OFEC Sweep

Command:

```bash
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 5000 --max-blocks 1000 --batch-blocks 16 --seed 42 --block-width 14 --codec-mode batched --time-budget-s 1800 --output-dir results/raw
```

The runner imports the real local `reproduce_fig3_baseline.py` and calls its
same-process `simulate_snr_point()` function. It uses `parallel_mode=serial`
because OFEC's process-worker paths stringify backend objects. It uses
`codec_mode=batched` so the real OFEC hard-stage path exercises
`EBCH256_239.decode_many`.

Raw CSVs in the bundle:

- `ofec_block_lut_backend/results/raw/real_ofec_syndrome_lut_ber.csv`
- `ofec_block_lut_backend/results/raw/real_ofec_block_lut_ber.csv`
- `ofec_block_lut_backend/results/raw/real_ofec_curve_diff.csv`
- `ofec_block_lut_backend/results/raw/real_ofec_timing.csv`

## BER Match

All six SNR points matched exactly:

- SNR: `13.7, 13.8, 13.9, 14.0, 14.1, 14.2`
- `total_blocks_delta = 0`
- `emitted_blocks_delta = 0`
- `total_bits_delta = 0`
- `pre_fec_errors_delta = 0`
- `post_fec_errors_delta = 0`
- `pre_fec_ber_delta = 0.0`
- `post_fec_ber_delta = 0.0`

The BER curve is therefore unchanged point by point after injecting the
block-LUT backend into the real OFEC chain.

## Timing

From `real_ofec_timing.csv`:

| quantity | syndrome_lut | block_lut | ratio syndrome_lut/block_lut |
|---|---:|---:|---:|
| total point wall-clock s | 58.89823750004871 | 52.053269700089004 | 1.13149928600831 |
| total wall-clock incl. common table init s | 61.048795700015035 | 54.20382790005533 | 1.126282000093811 |
| total decode s | 49.7945703008445 | 43.503093599225394 | 1.1446213632432598 |
| total input blocks | 5024 | 5024 | n/a |
| total emitted measurement blocks | 4424 | 4424 | n/a |

Common OFEC syndrome-table construction is recorded separately. Block-LUT
backend construction is included in `point_wall_sec` through
`external_backend_init_sec`.

## BER Rows

The two backend CSVs have identical BER/error rows. Shared post-FEC rows:

| SNR dB | total blocks | emitted blocks | post errors | post BER | stop |
|---:|---:|---:|---:|---:|---|
| 13.7 | 352 | 252 | 5009 | 0.004852779327876984 | target_errors_reached |
| 13.8 | 672 | 572 | 5063 | 0.0021609859866695805 | target_errors_reached |
| 13.9 | 1000 | 900 | 847 | 0.0002297634548611111 | max_blocks_reached |
| 14.0 | 1000 | 900 | 501 | 0.00013590494791666666 | max_blocks_reached |
| 14.1 | 1000 | 900 | 426 | 0.00011555989583333333 | max_blocks_reached |
| 14.2 | 1000 | 900 | 338 | 9.168836805555555e-05 | max_blocks_reached |

This is a real OFEC short run, not an M2 product-code run and not a 1e-8 floor
claim.

## Budget And Estimates

The run completed under the 30 minute budget. Lowest observed BER in this run:

- `9.168836805555555e-05` at `14.2 dB`

Throughput-based estimates for collecting 100 post errors at lower target BER,
using 4096 measured bits per emitted OFEC block and the observed emitted-block
wall time:

| target BER | emitted blocks | syndrome_lut estimate | block_lut estimate |
|---:|---:|---:|---:|
| 1e-6 | 24415 | 5.4174 min | 4.7878 min |
| 1e-7 | 244141 | 54.1722 min | 47.8765 min |
| 1e-8 | 2441407 | 541.7216 min | 478.7644 min |

These are planning estimates only.

## Verification

Commands run:

```bash
python -B -m pytest tests -q
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 5000 --max-blocks 1000 --batch-blocks 16 --seed 42 --block-width 14 --codec-mode batched --time-budget-s 1800 --output-dir results/raw
python -B -m pytest
```

Results:

- external backend tests: `2 passed, 1 warning`
- real OFEC sweep: `points=6 matched=True syndrome_lut_over_block_lut=1.1315`
- `fec_linear_backend` full test suite: `306 passed, 1 skipped, 27 warnings`

## Not Done

- No OFEC source-tree modifications.
- No process-parallel object injection, because OFEC's worker path stringifies
  backend objects.
- No 1e-8 floor run.
- No M2 product-code curve reused for this evidence.
