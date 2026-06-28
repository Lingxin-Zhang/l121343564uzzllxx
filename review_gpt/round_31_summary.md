# Round 31 Summary: Stable Paper Figures And Fig. 4 Shoulder

## Scope

This round converts the Round30 evidence into the requested paper-figure
artifacts and adds the missing low-SNR shoulder for the real OFEC BER curve.
The round did not edit the OFEC source tree.

Review bundle:

- `round31_review_bundle.zip`

New scripts:

- `benchmarks/bench_round31_cache_width.py`
- `scripts/plot_round31_fig2_throughput.py`
- `scripts/plot_round31_fig3_cache_width.py`
- `scripts/plot_round31_fig4_ber.py`

New test:

- `tests/test_round31_artifacts.py`

## Fig. 2

Output files:

- `results/figures/round31_fig2_actual_throughput.png`
- `results/figures/round31_fig2_actual_throughput.pdf`

CSV:

- `results/raw/round31_fixed_map_throughput.csv`
- `results/raw/round31_fig2_throughput_summary.csv`

Fig. 2 now uses absolute throughput on the y-axis. It does not use a speedup
y-axis. The plotted backend labels are neutral:

- direct vectorized GF(2) matmul
- block-LUT (cache-aware)
- naive per-codeword

The adopted run explicitly reads the Round31 width sweep and uses `w=14` for
BCH(255,239) r16. Batch `1` is retained and shows block-LUT below the direct
baseline for both syndrome and parity.

Peak BCH(255,239) r16 ratios in the plotted data:

- syndrome: `13.127147x` at batch `1000`, `486.827005 Mbit/s`
- parity: `9.527267x` at batch `1000`, `527.710227 Mbit/s`

The adopted Fig. 2 run took `1642.699 s`. A prior run used the old default
block-width source and was overwritten rather than reported.

## Fig. 3

Output files:

- `results/figures/round31_fig3_cache_width.png`
- `results/figures/round31_fig3_cache_width.pdf`

CSV:

- `results/raw/round31_block_width_cache_sweep.csv`
- `results/raw/round31_block_width_batch_sweep.csv`
- `results/raw/round31_same_tier_dram_proxy.csv`
- `results/raw/round31_cache_width_summary.csv`

The main Fig. 3 sweep covers `w=4..24`, batch `1000`, syndrome task, four BCH
profiles, `warmups=30`, `repeats=15`, exactness before speed, and safe skip for
oversized LUT tables.

Best measured widths in the multicode batch-1000 sweep:

| profile | best w | throughput Mbit/s | CV | cache fit |
|---|---:|---:|---:|---|
| BCH(255,239), r16 | 14 | 533.249650 | 0.036438 | L2 |
| BCH(255,231), r24 | 14 | 532.247921 | 0.011267 | L2 |
| BCH(511,484), r27 | 14 | 529.149829 | 0.273345 | L3 |
| BCH(1023,993), r30 | 10 | 483.094055 | 0.043067 | L2 |

Prediction fields are stored in the CSV. For BCH(255,239) r16, the predicted
L1/L2/L3 boundary widths are `9 / 14 / 19`, matching the measured batch-1000
choice of `w=14` in the multicode sweep. For BCH(1023,993) r30, the measured
best width moves left to `w=10`, consistent with larger table entries increasing
cache pressure.

Batch-sweep control for BCH(255,239) r16 shows noticeable drift:

| batch | best w | throughput Mbit/s | CV | cache fit |
|---:|---:|---:|---:|---|
| 100 | 21 | 327.342701 | 0.436173 | DRAM |
| 1000 | 22 | 484.883015 | 0.032465 | DRAM |
| 10000 | 12 | 454.959048 | 0.189781 | L2 |
| 100000 | 18 | 222.434674 | 0.070831 | L3 |
| 300000 | 24 | 210.305578 | 0.042340 | DRAM |

This is not used as a final architecture claim. It is reported as a stability
warning: the current Python-level benchmark still has enough noise that
high-repeat platform-pinned follow-up is needed before using the drifting
batch-wise maxima as a strong paper conclusion.

Same-tier control:

- natural mode best: `w=16`, `687.887727 Mbit/s`
- cache-flushed DRAM-proxy best: `w=8`, `20.407837 Mbit/s`

The proxy mode is a repeatable software cache-disruption control, not a
hardware-forced DRAM measurement.

## Fig. 4

Output files:

- `results/figures/round31_fig4_real_ofec_ber.png`
- `results/figures/round31_fig4_real_ofec_ber.pdf`

CSV:

- `results/raw/round31_fig4_low_snr_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_curve_diff.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_timing.csv`
- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

The plotted h16 curve uses:

- new low-SNR shoulder `13.50..13.70`, seed `42`;
- reused accepted R30 h16 formal points `13.75..13.95`;
- no `14.00 dB` zero-error upper-bound point.

All 10 paired points match exactly between the reference backend and block-LUT
backend. The diff CSV reports zero deltas for counts and BER fields.

BER rows used in the plot:

| SNR Es/N0 dB | post errors | BER | stop reason |
|---:|---:|---:|---|
| 13.50 | 748351 | 9.456671e-03 | target_errors_reached |
| 13.55 | 664632 | 8.398741e-03 | target_errors_reached |
| 13.60 | 583598 | 7.374740e-03 | target_errors_reached |
| 13.65 | 489459 | 6.185136e-03 | target_errors_reached |
| 13.70 | 379039 | 4.789794e-03 | target_errors_reached |
| 13.75 | 231439 | 2.924620e-03 | target_errors_reached |
| 13.80 | 56183 | 7.099665e-04 | target_errors_reached |
| 13.85 | 1399 | 1.767871e-05 | target_errors_reached |
| 13.90 | 291 | 4.085859e-07 | target_errors_reached |
| 13.95 | 9 | 5.169550e-09 | max_blocks_reached |

The `13.95 dB` point is low confidence because it has only 9 post-FEC errors,
and the figure draws it as an open marker. Interpolating the plotted h16 tail
puts `1e-7` around `13.92 dB`; this is reported only as a visual guide because
the tail includes that low-event point.

## Runtime Budget

All Round31 experiment processes completed under the per-process 1-hour limit.
No partial point was accepted under timeout.

Observed status-file durations:

- Fig. 3 multicode sweep: about `18.7 s`
- Fig. 3 multibatch sweep: about `678.6 s`
- Fig. 3 same-tier proxy sweep: about `17.3 s`
- Fig. 4 low-SNR shoulder sweep: about `996.5 s`
- adopted Fig. 2 throughput rerun: `1642.699 s`

## Verification

Round31 smoke:

```powershell
python -B -m pytest tests/test_round31_artifacts.py -q
```

Result:

- `4 passed, 1 warning`

Full suite:

```powershell
python -B -m pytest tests -q
```

Result:

- `314 passed, 1 skipped, 27 warnings`

## Remaining Cautions

- Fig. 3 still shows noise in several rows. This round keeps the raw median,
  min/max-derived bars, and CV fields visible rather than smoothing them away.
- The same-tier `cache_flushed_dram_proxy` result is useful as a disruption
  control, but it should not be described as a hardware DRAM-only measurement.
- Fig. 4's `13.95 dB` BER is a low-event tail point. It supports curve shape and
  paired exactness, but not a high-confidence BER floor estimate by itself.
