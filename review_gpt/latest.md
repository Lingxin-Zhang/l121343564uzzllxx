# Latest Review Summary

Current round: Round 35.

## Scope

This round adds one real OFEC Fig. 2 companion sweep at the same plotted SNR
grid as the existing Fig. 2 data, but with `h=12` instead of `h=16`.

The original Fig. 2 image files were not overwritten. The new overlay figure is
written under a new stem:

- `results/figures/round35_fig2_real_ofec_h12_h16_overlay.png`
- `results/figures/round35_fig2_real_ofec_h12_h16_overlay.pdf`

## Inputs And Command

The existing Fig. 2 curve remains the Round31 h16 real OFEC data:

- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

The h12 sweep was run in the external simulator package:

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

Different SNR/backend points were run with `point_parallel_workers=3`; each
point used `mc_workers=6`.

## New Data

Copied h12 CSVs:

- `results/raw/round35_fig2_h12_same_grid_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_block_lut_ber.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_curve_diff.csv`
- `results/raw/round35_fig2_h12_same_grid_real_ofec_timing.csv`

All 10 h12 SNR points match exactly between the bit-parallel/reference path and
the block-LUT path: `post_fec_errors_delta=0` and `post_fec_ber_delta=0.0` for
every row.

The h12 `13.95 dB` point is measured, not trend-filled:

- `post_fec_errors=130`
- `post_fec_ber=7.537351869003515e-08`
- `stop_reason=max_blocks_reached`

## Figure Script

New script:

- `scripts/plot_round35_fig2_h12_overlay.py`

The plot legend uses the requested neutral display label:

- `bit-parallel GF(2)` for the reference/syndrome LUT path
- `block-LUT` for the injected block-LUT path

The raw CSV backend names are unchanged.

## Timing

From `round35_fig2_h12_same_grid_real_ofec_timing.csv`:

- bit-parallel/reference path total point wall: `3692.2095526000485 s`
- block-LUT path total point wall: `3596.9286567999516 s`
- recorded point-wall ratio: `1.026490x`
- recorded decode-sec ratio: `1.029349x`

These timing values are recorded for audit; the new Fig. 2 overlay is a BER
equivalence plot.

## Verification

```powershell
python -B -m pytest tests\test_round35_fig2_overlay.py tests\test_round34_artifacts.py -q
python -B -m pytest -q
```

Results:

- targeted smoke: `4 passed, 1 warning`
- full suite: `328 passed, 1 skipped, 27 warnings`
