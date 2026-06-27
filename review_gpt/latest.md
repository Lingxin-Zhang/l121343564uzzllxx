# Latest Review Summary

Current round: Round 30 review snapshot.

## Scope

Round 30 extends the real local OFEC evidence from Round 29:

- keep `D:\PKU\OFEC\project\ofec-0.1.0` read-only;
- inject the external `BlockLUTBCHBackend` from
  `D:\PKU\acp2026\ofec_block_lut_backend`;
- verify real OFEC BER curves remain pointwise identical after replacing only
  the BCH syndrome/parity backend;
- regenerate Fig. 2/Fig. 3/Fig. 4-style real OFEC BER figures from CSVs.
- rerun Fig. 2/Fig. 3 fixed-map data with higher repeats.

Review bundle path:

- `round30_real_ofec_review_snapshot.zip`

## Parallel Injection Gate

The external runner now supports point-level process parallelism. Each worker
self-constructs its backend from a backend label plus fixed parameters instead
of receiving a pickled backend object. This avoids modifying OFEC source files.

Gate result:

- serial vs point-parallel, 3 SNR points: all BER/error/count fields matched;
- external backend tests: `3 passed, 1 warning`.

Important boundary: OFEC's built-in `mc` worker path still stringifies backend
objects, so it was not used as block-LUT paired evidence. The paired evidence
below comes from the external runner that calls the real OFEC
`simulate_snr_point()` in each worker.

## Primary h=10 Sweep

Source CSVs:

- `results/raw/round30_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_real_ofec_block_lut_ber.csv`
- `results/raw/round30_real_ofec_curve_diff.csv`
- `results/raw/round30_real_ofec_timing.csv`

Run parameters:

- h: `10`
- SNR Es/N0: `13.70` to `15.95` dB, step `0.25`
- `min_post_errors=100`
- `max_blocks=60000`
- `batch_blocks=16`
- `block_width=14`
- external measured wall-clock: `1124.2542795 s`

All 10 paired points matched exactly:

- `total_blocks_delta = 0`
- `emitted_blocks_delta = 0`
- `total_bits_delta = 0`
- `pre_fec_errors_delta = 0`
- `post_fec_errors_delta = 0`
- `pre_fec_ber_delta = 0.0`
- `post_fec_ber_delta = 0.0`

Lowest primary-sweep BER:

- `1.0597088898163606e-07` at `15.95 dB`
- `26 / 245350400` post-FEC bit errors
- stop reason: `max_blocks_reached`

This is close to `1e-7` but is below the requested 100-error reliability
threshold, so it is reported as an observed low-error point, not a precision
floor claim.

## Timing

From `round30_real_ofec_timing.csv`:

| metric | syndrome_lut | block_lut | ratio |
|---|---:|---:|---:|
| summed point wall s | 4452.421527999919 | 4335.98079149978 | 1.026854532365182 |
| summed wall incl. common init s | 4469.39580150001 | 4352.811351599812 | 1.0267837129806576 |
| summed decode s | 3875.640491998871 | 3765.669281698705 | 1.0292036294410212 |

These are end-to-end real OFEC ratios for this runner, not isolated-kernel
speedups.

## Extension Probe

Two additional h=10 points were run after the primary sweep:

- `16.20 dB`: `8.559187186978297e-08`, `21 / 245350400`
- `16.45 dB`: `9.781928213689482e-08`, `24 / 245350400`

Both extension points matched exactly between backends. They are kept in
separate CSVs and are not mixed into the primary 10-point curve because the
later h-window discussion made these high-SNR points questionable for the
intended paper framing.

## h Calibration Probe

Additional MC-style calibration data exists in:

- `results/raw/round30_h_calibration_mc_summary.csv`

It is useful for discussion only and is not paired block-LUT evidence.

Summary:

| h | rows | approx BER=1e-3 SNR | best positive BER | first zero-error SNR | sec/input block |
|---:|---:|---:|---:|---:|---:|
| 15 | 12 | 13.786148850324029 | 1.7447905106977983e-06 @ 13.9 | 14.0 | 0.004691350227004699 |
| 18 | 12 | 13.758343935901685 | 5.6425730387369794e-06 @ 13.9 | 14.0 | 0.00525976700398677 |
| 20 | 12 | 13.764714867870186 | 0.0004134178161621094 @ 13.8 | 13.9 | 0.005769333680676488 |
| 22 | 6 | 13.757065915664533 | 0.00030863285064697266 @ 13.8 | 13.9 | 0.008848963103144458 |

The zero-error rows mean finite-sample zero observations, not BER equal to zero.
These h values are not part of the current h=10 primary conclusion.

## SNR Definition

The local OFEC channel uses normalized 16QAM with average symbol power 1 and
noise variance per real dimension `1 / (2 * SNR_linear)`. The figure axis is
therefore labeled `SNR Es/N0 (dB)`.

## High-Repeat Fixed-Map Data

New high-repeat CSVs:

- `results/raw/block_width_cache_sweep_highrep.csv`
- `results/raw/fixed_map_three_backend_highrep.csv`

Settings:

- repeats: `15`
- warmups: `3`
- block-width batch sizes: `1000, 10000, 100000, 300000`
- three-backend batch sizes: `1, 10, 100, 1000, 10000, 100000, 300000`
- max timed batch size: `300000`
- galois per-codeword timing capped at batch `1000`

Exactness/timing summary:

- block-width high-repeat: 176 rows, 176 exactness pass, 164 timed;
- three-backend high-repeat: 96 rows, 96 exactness pass, 72 timed.

Fig. 3 now plots from the high-repeat CSV. The r16 panel uses batch `300000`;
the r27 panel uses batch `10000`, selected because the high-repeat
`batch=1000` row still had visible small-batch noise.

The r27 curve is improved versus the old `batch=1000` panel, but it still has a
small secondary bump around `w=13`. The result is reported as measured data,
not smoothed or edited.

## Figures

Generated from committed CSVs:

- `results/figures/round30_real_ofec_ber.png`
- `results/figures/round30_real_ofec_ber.pdf`
- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`
- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`

Fig. 3 now uses block width `w` in the axis label and peak annotation.

## Not Done In This Snapshot

- No final `min_post_errors=200`, `max_blocks=500000` h=10 one-hour capped
  sweep was completed. The current primary curve is the completed 10-point
  `max_blocks=60000` review sweep.
- No OFEC source-tree file was modified.

## Verification

Fresh verification commands:

```powershell
python -B -m pytest tests -q
python -B -m pytest -q
```

Results:

- external package: `3 passed, 1 warning`
- `fec_linear_backend`: `308 passed, 1 skipped, 27 warnings`
