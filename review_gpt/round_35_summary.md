# Round 35 Summary: Fig. 2 h12 Overlay

## Scope

Round 35 adds an `h=12` real OFEC sweep on the same plotted SNR grid used by
the current Fig. 2 h16 curve and redraws a new overlay figure without
overwriting the existing Fig. 2 files.

No OFEC source file was modified. The h12 sweep was run in the external package
`D:\PKU\acp2026\ofec_block_lut_backend`, and the generated CSVs were copied
into this repository for reproducible plotting.

## Existing Fig. 2 Data

The existing curve is unchanged and reads:

- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

It uses `h=16`, SNR Es/N0 grid `13.50..13.95` with step `0.05`, and all 10
paired rows have zero post-FEC error and BER deltas.

## h12 Sweep

Command:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep `
  --snr-min 13.5 --snr-max 13.95 --snr-step 0.05 `
  --h 12 --min-post-errors 200 --max-blocks 500000 `
  --batch-blocks 16 --seed 42 --block-width 14 `
  --target-post-ber 1e-9 --codec-mode batched `
  --time-budget-s 3600 --measurement-mode mc --mc-workers 6 `
  --accept-time-capped-min-errors 60 --point-parallel-workers 3 `
  --output-dir D:\PKU\acp2026\ofec_block_lut_backend\results\round35_fig2_h12_same_grid
```

Different SNR/backend jobs ran in parallel with `point_parallel_workers=3`.
Each job used `mc_workers=6`.

Runner output:

```text
points=10 matched=True syndrome_lut_over_block_lut=1.02649
```

Copied CSVs:

- `results/raw/round35_fig2_h12_same_grid_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_block_lut_ber.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_curve_diff.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_timing.csv`

Accepted h12 rows:

| SNR Es/N0 dB | post errors | BER | stop reason |
|---:|---:|---:|---|
| 13.50 | 566223 | `9.520525971720041e-03` | target_errors_reached |
| 13.55 | 502860 | `8.45513462035124e-03` | target_errors_reached |
| 13.60 | 436708 | `7.342848764634986e-03` | target_errors_reached |
| 13.65 | 369608 | `6.214623149104683e-03` | target_errors_reached |
| 13.70 | 285416 | `4.799011062327824e-03` | target_errors_reached |
| 13.75 | 180886 | `3.041433959624656e-03` | target_errors_reached |
| 13.80 | 59013 | `9.922500484245867e-04` | target_errors_reached |
| 13.85 | 6535 | `1.0988009534263086e-04` | target_errors_reached |
| 13.90 | 317 | `5.330067363980716e-06` | target_errors_reached |
| 13.95 | 130 | `7.537351869003515e-08` | max_blocks_reached |

The `13.95 dB` h12 point is measured from 130 post-FEC errors. No trend-filled
or invented BER value is used.

## Plotting

New script:

- `scripts/plot_round35_fig2_h12_overlay.py`

New figure files:

- `results/figures/round35_fig2_real_ofec_h12_h16_overlay.png`
- `results/figures/round35_fig2_real_ofec_h12_h16_overlay.pdf`

The plotting layer uses the neutral legend label `bit-parallel GF(2)` for the
reference/syndrome LUT path. Raw CSV backend names are unchanged.

The existing Round34 Fig. 2 plotting script label was also updated from
`reference syndrome backend` to `bit-parallel GF(2)` for future redraws:

- `scripts/plot_round34_fig2_ber_overlap.py`

The existing Round34 Fig. 2 output files were not overwritten by the h12
overlay command.

## Timing

From `round35_fig2_h12_same_grid_real_ofec_timing.csv`:

| backend | points | total point wall s | total decode s |
|---|---:|---:|---:|
| bit-parallel/reference path | 10 | `3692.2095526000485` | `18884.954620` |
| block-LUT path | 10 | `3596.9286567999516` | `18346.507171` |

Recorded ratios:

- point-wall ratio: `1.026490x`
- decode-sec ratio: `1.029349x`

## Verification

Targeted smoke:

```powershell
python -B -m pytest tests\test_round35_fig2_overlay.py tests\test_round34_artifacts.py -q
```

Result: `4 passed, 1 warning`.

Full suite:

```powershell
python -B -m pytest -q
```

Result: `328 passed, 1 skipped, 27 warnings`.
