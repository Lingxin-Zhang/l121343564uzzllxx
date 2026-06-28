# Latest Review Summary

Current round: Round 31 review snapshot.

Review bundle path:

- `round31_review_bundle.zip`

## Scope

Round 31 is a post-R30 stabilization and paper-figure refresh round:

- Fig. 2 is redrawn as absolute online throughput, not speedup.
- Fig. 3 is rerun as a wider block-width/cache sweep over `w=4..24`.
- Fig. 4 reuses the accepted R30 `h=16` deep points and adds only the
  low-SNR shoulder points `13.50..13.70`.
- The OFEC source tree remains read-only; no source files under
  `D:\PKU\OFEC\project\ofec-0.1.0` were edited.

All reported values below are read from committed CSV outputs. No paper figure
uses specific software-library names in labels or legends.

## New Or Updated Artifacts

Benchmark and plotting scripts:

- `benchmarks/bench_round31_cache_width.py`
- `scripts/plot_round31_fig2_throughput.py`
- `scripts/plot_round31_fig3_cache_width.py`
- `scripts/plot_round31_fig4_ber.py`

Smoke test:

- `tests/test_round31_artifacts.py`

Raw CSV outputs:

- `results/raw/round31_block_width_cache_sweep.csv`
- `results/raw/round31_block_width_batch_sweep.csv`
- `results/raw/round31_same_tier_dram_proxy.csv`
- `results/raw/round31_cache_width_summary.csv`
- `results/raw/round31_fixed_map_throughput.csv`
- `results/raw/round31_fig2_throughput_summary.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_curve_diff.csv`
- `results/raw/round31_fig4_low_snr_real_ofec_timing.csv`
- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

Figures:

- `results/figures/round31_fig2_actual_throughput.png`
- `results/figures/round31_fig2_actual_throughput.pdf`
- `results/figures/round31_fig3_cache_width.png`
- `results/figures/round31_fig3_cache_width.pdf`
- `results/figures/round31_fig4_real_ofec_ber.png`
- `results/figures/round31_fig4_real_ofec_ber.pdf`

## Fig. 2: Absolute Throughput

Data source:

- `results/raw/round31_fixed_map_throughput.csv`

Plot script:

- `scripts/plot_round31_fig2_throughput.py`

Display labels are neutralized in the plotting layer:

- `PackedBatchGF2Kernel.apply_many` -> `direct vectorized GF(2) matmul`
- `PackedBlockLUTKernel.apply_many_packed` -> `block-LUT (cache-aware)`
- `galois_per_codeword` -> `naive per-codeword`

The adopted Fig. 2 run uses Round31 cache-sweep width source explicitly:

- `--block-width-source results/raw/round31_block_width_cache_sweep.csv`
- `--selection-batch-size 1000`
- resulting displayed BCH(255,239) block-LUT width: `w=14`

The first Fig. 2 attempt accidentally used the older default
`results/raw/block_width_cache_sweep.csv`, which selected `w=13` for the r16
rows. That output was overwritten and is not used.

Selected BCH(255,239) r16 rows:

| task | batch | direct Mbit/s | block-LUT Mbit/s | LUT/direct |
|---|---:|---:|---:|---:|
| syndrome | 1 | 17.229734 | 4.473687 | 0.259649 |
| syndrome | 100 | 83.061918 | 99.415215 | 1.196881 |
| syndrome | 1000 | 37.085514 | 486.827005 | 13.127147 |
| syndrome | 100000 | 43.529918 | 223.721694 | 5.139493 |
| syndrome | 300000 | 39.107838 | 200.986383 | 5.139286 |
| parity | 1 | 17.835840 | 4.704721 | 0.263779 |
| parity | 100 | 36.561109 | 277.584343 | 7.592339 |
| parity | 1000 | 55.389464 | 527.710227 | 9.527267 |
| parity | 100000 | 43.737503 | 195.285210 | 4.464937 |
| parity | 300000 | 40.554535 | 206.478173 | 5.091371 |

Batch `1` remains below the direct baseline and is kept in the figure.

## Fig. 3: Block Width And Cache

Data sources:

- `results/raw/round31_block_width_cache_sweep.csv`
- `results/raw/round31_block_width_batch_sweep.csv`
- `results/raw/round31_same_tier_dram_proxy.csv`
- `results/raw/round31_cache_width_summary.csv`

Plot script:

- `scripts/plot_round31_fig3_cache_width.py`

Benchmark settings:

- block widths: `w=4..24`
- main Fig. 3 batch: `1000`
- task: syndrome
- warmups/repeats: `30` / `15`
- exactness checked before timing for every timed row
- maximum LUT table budget: `402653184` bytes; oversized rows are marked
  skipped instead of forced

Best measured widths from the multicode batch-1000 sweep:

| profile | best w | throughput Mbit/s | CV | cache fit | table bytes | predicted L1/L2/L3 w |
|---|---:|---:|---:|---|---:|---|
| BCH(255,239), r16 | 14 | 533.249650 | 0.036438 | L2 | 622592 | 9 / 14 / 19 |
| BCH(255,231), r24 | 14 | 532.247921 | 0.011267 | L2 | 933888 | 8 / 14 / 18 |
| BCH(511,484), r27 | 14 | 529.149829 | 0.273345 | L3 | 2424832 | 6 / 12 / 17 |
| BCH(1023,993), r30 | 10 | 483.094055 | 0.043067 | L2 | 421888 | 5 / 11 / 16 |

The r30 case shifts the best observed width left to `w=10`, consistent with
larger per-entry storage increasing cache pressure. The r27 row is noisy
(`CV=0.273345`) and should not be over-interpreted.

Batch-drift control for BCH(255,239) r16:

| batch | best w | throughput Mbit/s | CV | cache fit |
|---:|---:|---:|---:|---|
| 100 | 21 | 327.342701 | 0.436173 | DRAM |
| 1000 | 22 | 484.883015 | 0.032465 | DRAM |
| 10000 | 12 | 454.959048 | 0.189781 | L2 |
| 100000 | 18 | 222.434674 | 0.070831 | L3 |
| 300000 | 24 | 210.305578 | 0.042340 | DRAM |

This batch sweep shows substantial small-run drift. It is kept as a data
quality warning, not as a claim that very large DRAM-sized tables are generally
best. Follow-up high-repeat platform-pinned runs should validate the stable
batch regime.

Same-tier memory control:

- natural measurement best: `w=16`, `687.887727 Mbit/s`, `CV=0.018128`, L3 fit
- cache-flushed DRAM-proxy best: `w=8`, `20.407837 Mbit/s`, `CV=0.019061`, L1 fit

The DRAM-proxy mode touches a flush buffer before each timing call. It is a
software proxy for cache disruption, not a hardware guarantee that every table
lookup is served from DRAM.

The right-axis compute guide uses the continuous monotone trend
`input_width / w`. The CSV also stores the raw ceiling-based count
`ceil(input_width / w)`.

## Fig. 4: Real OFEC BER

Data sources:

- low shoulder, seed 42:
  `results/raw/round31_fig4_low_snr_real_ofec_*`
- reused accepted R30 h16 formal points:
  `results/raw/round31_fig4_real_ofec_*`

Plot script:

- `scripts/plot_round31_fig4_ber.py`

The plotted curve contains `13.50..13.95 dB`; the `14.00 dB` zero-error upper
bound point is excluded. The low-SNR shoulder points `13.50..13.70` were run in
this round with seed `42`. The deeper `13.75..13.95` points are reused from the
accepted R30 h16 formal sweep, as requested for Round31.

All 10 paired reference/backend rows match exactly:

- `post_fec_errors_delta = 0`
- `pre_fec_errors_delta = 0`
- BER deltas are `0`

Selected BER rows:

| SNR Es/N0 dB | post errors | BER | wall s | stop reason |
|---:|---:|---:|---:|---|
| 13.50 | 748351 | 9.456671e-03 | 100.091735 | target_errors_reached |
| 13.70 | 379039 | 4.789794e-03 | 94.802907 | target_errors_reached |
| 13.80 | 56183 | 7.099665e-04 | 94.414413 | target_errors_reached |
| 13.85 | 1399 | 1.767871e-05 | 95.297739 | target_errors_reached |
| 13.90 | 291 | 4.085859e-07 | 810.943356 | target_errors_reached |
| 13.95 | 9 | 5.169550e-09 | 1996.622509 | max_blocks_reached |

The `13.95 dB` point has fewer than 10 post-FEC errors and is drawn with an
open marker. A log-linear interpolation between `13.90` and `13.95` places the
`1e-7` crossing near `13.92 dB`, but that tail estimate inherits the low-event
uncertainty of the `13.95 dB` point.

## Timing And Limits

No Round31 background experiment hit the 1-hour per-process kill limit.

Observed wall times from status files:

- Fig. 3 multicode sweep: about `18.7 s`
- Fig. 3 multibatch sweep: about `678.6 s`
- Fig. 3 same-tier proxy sweep: about `17.3 s`
- Fig. 4 low-SNR shoulder sweep: about `996.5 s`
- adopted Fig. 2 throughput rerun: `1642.699 s`

The Fig. 2 first run is not adopted because it used the old width source.

## Verification

Round31 smoke test:

- `python -B -m pytest tests/test_round31_artifacts.py -q`
- result: `4 passed, 1 warning`

Full test suite:

- `python -B -m pytest tests -q`
- result: `314 passed, 1 skipped, 27 warnings`
