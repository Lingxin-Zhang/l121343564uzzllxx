# Round 30 Summary: Real OFEC BER Review Snapshot

## Scope And Boundary

This round keeps the OFEC source tree read-only:

- OFEC source: `D:\PKU\OFEC\project\ofec-0.1.0`
- external injection package: `D:\PKU\acp2026\ofec_block_lut_backend`

The external package still reuses OFEC's official BCH syndrome tables and
error-locator arrays. The block-LUT backend replaces only the online fixed
GF(2) syndrome/parity evaluation.

Review bundle:

- `round30_real_ofec_review_snapshot.zip`

The bundle contains the external backend/runner files, paired real-OFEC BER
CSVs/diffs/timing, h16/h18 MC-core follow-up CSVs, high-repeat Fig. 2/Fig. 3
CSVs, generated PNG/PDF figures, plot scripts, tests, these review notes, and
`review_gpt/round_30_completion_audit.md`.

## Implementation Delta

External runner update:

- `ofec_block_lut_backend/ofec_block_lut_backend/run_real_ofec_sweep.py`

The runner now supports `--point-parallel-workers`. Each worker receives a
plain backend label and constructs its backend locally:

- `syndrome_lut` -> official OFEC syndrome-LUT backend name;
- `block_lut` -> `BlockLUTBCHBackend(255, 239, block_width=14)`.

No instantiated backend object is pickled into a worker.

The runner also now supports an external MC measurement mode for paired
backend runs. In that mode each worker constructs its own backend and MC chunks
are aggregated wave-synchronously before applying the stop rule, so the
reference backend and block-LUT backend consume the same seed/chunk set. This
fix avoids backend-speed-dependent early stopping. A h18 refine run produced
before this fix is not used as evidence.

The MC runner also supports time-capped points and filters interrupted
time-capped pairs unless the post-FEC error count is greater than the
configured acceptance threshold. The current default threshold is `60`, matching
the later "greater than 60 errors" instruction for interrupted final points.

Test update:

- `ofec_block_lut_backend/tests/test_block_lut_backend_equivalence.py`

The added test verifies that point-parallel output matches serial output for
the same seeds.

Additional MC-mode tests verify that paired backends match after
warmup/measure/discard, early stopping keeps the same chunk count for both
backends, and low-error time-capped pairs are not written as accepted BER rows.

Repository plotting updates:

- `scripts/plot_round30_real_ofec_ber.py`
- `scripts/plot_paper_fig3.py`
- `tests/test_paper_round27_plots.py`

Fig. 3's block-width display now uses `w`, not `a`.

## Parallel Gate

Commands used for the gate:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 13.9 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 160 --batch-blocks 16 --seed 42 --block-width 14 --codec-mode batched --time-budget-s 600 --point-parallel-workers 1 --output-dir results/round30_parallel_gate_serial
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 13.9 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 160 --batch-blocks 16 --seed 42 --block-width 14 --codec-mode batched --time-budget-s 600 --point-parallel-workers 4 --output-dir results/round30_parallel_gate_parallel
```

CSV comparison:

- `real_ofec_syndrome_lut_ber.csv`: 3/3 rows identical;
- `real_ofec_block_lut_ber.csv`: 3/3 rows identical;
- `real_ofec_curve_diff.csv`: 3/3 rows identical.

External wall-clock from `Measure-Command`:

- serial gate: `6.7426238 s`
- point-parallel gate: `6.3129987 s`
- wall ratio: about `1.068x`

This gate verifies the external point-parallel runner. It does not make OFEC's
built-in `mc` mode accept injected object backends; that path still stringifies
backend values in OFEC's own worker code.

## h=10 And h=15 Cheap Calibration

Paired h=10 calibration:

- SNR: `13.7` to `15.45`, step `0.25`
- `min_post_errors=50`
- `max_blocks=2000`
- all paired backend rows matched exactly.

Lowest h=10 calibration row:

- `15.45 dB`
- `38 / 7782400`
- BER `4.8828125e-06`
- stop: `max_blocks_reached`

Paired h=15 calibration:

- same SNR grid and limits;
- all paired backend rows matched exactly;
- h=15 did not produce a better low-BER point in this short calibration and
  had a higher per-emitted-block cost.

## Primary Real OFEC Sweep

Command:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 15.95 --snr-step 0.25 --h 10 --min-post-errors 100 --max-blocks 60000 --batch-blocks 16 --seed 62030 --block-width 14 --codec-mode batched --time-budget-s 3600 --point-parallel-workers 8 --output-dir results/round30_final_h10
```

External wall-clock:

- `1124.2542795 s`

Copied repository CSVs:

- `results/raw/round30_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_real_ofec_block_lut_ber.csv`
- `results/raw/round30_real_ofec_curve_diff.csv`
- `results/raw/round30_real_ofec_timing.csv`
- `results/raw/round30_real_ofec_wall_clock.csv`

All 10 SNR points matched exactly. The shared BER rows are:

| SNR Es/N0 dB | post errors | total bits | post-FEC BER | stop |
|---:|---:|---:|---:|---|
| 13.70 | 455 | 49152 | 0.009256998697916666 | target_errors_reached |
| 13.95 | 334 | 49152 | 0.006795247395833333 | target_errors_reached |
| 14.20 | 322 | 49152 | 0.006551106770833333 | target_errors_reached |
| 14.45 | 177 | 49152 | 0.00360107421875 | target_errors_reached |
| 14.70 | 137 | 49152 | 0.0027872721354166665 | target_errors_reached |
| 14.95 | 116 | 49152 | 0.0023600260416666665 | target_errors_reached |
| 15.20 | 61 | 245350400 | 2.486240087646077e-07 | max_blocks_reached |
| 15.45 | 34 | 245350400 | 1.38577316360601e-07 | max_blocks_reached |
| 15.70 | 30 | 245350400 | 1.2227410267111852e-07 | max_blocks_reached |
| 15.95 | 26 | 245350400 | 1.0597088898163606e-07 | max_blocks_reached |

Lowest primary-sweep row:

- `1.0597088898163606e-07` at `15.95 dB`
- error count: `26`

Because this is below 100 errors, it should be read as an observed low-error
point, not a high-confidence floor estimate.

## Primary Timing

From `results/raw/round30_real_ofec_timing.csv`:

| metric | syndrome_lut | block_lut | ratio syndrome_lut/block_lut |
|---|---:|---:|---:|
| summed point wall-clock s | 4452.421527999919 | 4335.98079149978 | 1.026854532365182 |
| summed wall-clock incl. common init s | 4469.39580150001 | 4352.811351599812 | 1.0267837129806576 |
| summed decode s | 3875.640491998871 | 3765.669281698705 | 1.0292036294410212 |
| total input blocks | 240672 | 240672 | n/a |
| total emitted blocks | 239672 | 239672 | n/a |

The ratio is a real OFEC end-to-end runner ratio. It is not the isolated
fixed-map speedup.

## Extension Probe

Command:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 16.2 --snr-max 16.45 --snr-step 0.25 --h 10 --min-post-errors 100 --max-blocks 60000 --batch-blocks 16 --seed 62040 --block-width 14 --codec-mode batched --time-budget-s 2400 --point-parallel-workers 4 --output-dir results/round30_final_h10_extend
```

External wall-clock:

- `932.5082207 s`

Both extension points matched exactly:

| SNR Es/N0 dB | post errors | total bits | post-FEC BER | stop |
|---:|---:|---:|---:|---|
| 16.20 | 21 | 245350400 | 8.559187186978297e-08 | max_blocks_reached |
| 16.45 | 24 | 245350400 | 9.781928213689482e-08 | max_blocks_reached |

These are kept as a separate high-SNR extension probe. They are not mixed into
the primary h=10 curve because the later discussion questioned using 16 dB
work points for the intended paper framing.

## h Calibration Probe

The user later requested h calibration around the literature-like waterfall
region. The partially/completely finished h-calibration results were preserved
as a separate probe:

- `results/raw/round30_h_calibration_mc_summary.csv`
- `results/raw/round30_h_selection_addendum.csv`

The probe used OFEC's `mc` mode and the official `syndrome_lut` backend, so it
is not paired block-LUT evidence.

| h | rows | approx BER=1e-3 SNR | best positive BER | first zero-error SNR | sec/input block |
|---:|---:|---:|---:|---:|---:|
| 15 | 12 | 13.786148850324029 | 1.7447905106977983e-06 @ 13.9 | 14.0 | 0.004691350227004699 |
| 18 | 12 | 13.758343935901685 | 5.6425730387369794e-06 @ 13.9 | 14.0 | 0.00525976700398677 |
| 20 | 12 | 13.764714867870186 | 0.0004134178161621094 @ 13.8 | 13.9 | 0.005769333680676488 |
| 22 | 6 | 13.757065915664533 | 0.00030863285064697266 @ 13.8 | 13.9 | 0.008848963103144458 |

The zero-error rows mean finite-sample zero observations. They are not claims
that the BER is zero.

For the specific question "which h puts the roughly `1e-6` to `1e-8`
waterfall region near `14.0 dB`", this official-backend calibration initially
made h=18 look like the best next candidate:

| h | 13.9 dB evidence | 14.0 dB evidence | current interpretation |
|---:|---|---|---|
| 15 | `1.7447905106977983e-06`, `161 / 92274688` | `0 / 151912448`, zero-error upper approx. `1.97e-8` | close backup; likely slightly earlier than 14.0 for `1e-7` |
| 18 | `5.6425730387369794e-06`, `142 / 25165824` | `0 / 148979712`, zero-error upper approx. `2.01e-8` | initially preferred candidate; later paired MC-core evidence favors h=16 |
| 20 | `0 / 145375232`, zero-error upper approx. `2.06e-8` | `0 / 145375232`, zero-error upper approx. `2.06e-8` | too strong/left-shifted for the requested target |
| 22 | `0 / 142606336`, zero-error upper approx. `2.10e-8` | `0 / 142606336`, zero-error upper approx. `2.10e-8` | too strong/left-shifted for the requested target |

Additional short probes for h12/h14/h15/h16 were run by parallel subagents
under the one-hour aggregate experiment budget. All reported probe points had
more than 60 post-FEC errors, so they are recorded. However, they stopped after
only 4 to 16 measurement blocks and are startup-transient dominated. They are
smoke data only and are not used to choose h.

## Paired MC-Core h16/h18 Follow-Up

After the user asked whether h=15/16 would be better than h=18, paired MC-core
experiments were run for h16 and h18 at `13.9` and `14.0 dB`. These runs use
both backends and therefore provide end-to-end paired exactness evidence, not
just official-backend calibration.

Copied repository CSVs:

- `results/raw/round30_formal_h16_mc_core_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_formal_h16_mc_core_real_ofec_block_lut_ber.csv`
- `results/raw/round30_formal_h16_mc_core_real_ofec_curve_diff.csv`
- `results/raw/round30_formal_h16_mc_core_real_ofec_timing.csv`
- `results/raw/round30_formal_h18_mc_core_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_formal_h18_mc_core_real_ofec_block_lut_ber.csv`
- `results/raw/round30_formal_h18_mc_core_real_ofec_curve_diff.csv`
- `results/raw/round30_formal_h18_mc_core_real_ofec_timing.csv`

Accepted rows:

| h | SNR Es/N0 dB | post errors | total bits | post-FEC BER / upper bound | stop | paired diff |
|---:|---:|---:|---:|---:|---|---|
| 16 | 13.9 | 188 | 67108864 | `2.8014183044433594e-06` | target_errors_reached | exact match |
| 16 | 14.0 | 0 | 671088640 | zero-error upper approx. `4.463988956260323e-09` | max_blocks_reached | exact match |
| 18 | 13.9 | 38 | 209715200 | `1.811981201171875e-07` | max_blocks_reached | exact match |
| 18 | 14.0 | 0 | 209715200 | zero-error upper approx. `1.4284764593419652e-08` | max_blocks_reached | exact match |

The current recommendation is h=16:

- h16 gives a positive, better-counted `13.9 dB` point (`188` post-FEC errors),
  and a `14.0 dB` zero-observation upper bound below `1e-8`.
- h18 is still paired bit-exact, but its `13.9 dB` point has only `38` errors,
  so it is too weak to be the main calibration evidence.
- h15 remains plausible from the official-backend calibration, but a full
  paired MC-core h15 run was not started because the aggregate experiment
  budget was already better spent analyzing the completed h16/h18 data.

Timing summary:

| h | syndrome_lut point wall s | block_lut point wall s | point-wall ratio | decode ratio |
|---:|---:|---:|---:|---:|
| 16 | 845.703773999936 | 806.358839299879 | `1.0487933321772949` | `1.0573324636310466` |
| 18 | 630.7593108000001 | 575.8718545000302 | `1.0953119272474656` | `1.058312426807149` |

Generated h16 paired figure:

- `results/figures/round30_real_ofec_h16_mc_ber.png`
- `results/figures/round30_real_ofec_h16_mc_ber.pdf`

The h16 figure plots zero-error points as 95% one-sided upper bounds on the
log-scale axis instead of plotting literal zero.

## Formal Fig. 4 h16 Sweep

After the later instruction to use the previously identified suitable h value
for the best Fig. 4, the formal Fig. 4 sweep was run with h=16:

- SNR Es/N0 grid: `13.75, 13.80, 13.85, 13.90, 13.95, 14.00`
- `min_post_errors=200`
- `max_blocks=500000`
- `batch_blocks=16`
- `measurement_mode=mc`
- `mc_workers=6`
- `block_width=14`

Copied repository CSVs:

- `results/raw/round30_fig4_h16_formal_6h_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_fig4_h16_formal_6h_real_ofec_block_lut_ber.csv`
- `results/raw/round30_fig4_h16_formal_6h_real_ofec_curve_diff.csv`
- `results/raw/round30_fig4_h16_formal_6h_real_ofec_timing.csv`

Accepted rows:

| SNR Es/N0 dB | post errors | total bits | post-FEC BER / upper bound | stop | paired diff |
|---:|---:|---:|---:|---|---|
| 13.75 | 231439 | 79134720 | `0.0029246201919966358` | target_errors_reached | exact match |
| 13.80 | 56183 | 79134720 | `0.0007099664976384576` | target_errors_reached | exact match |
| 13.85 | 1399 | 79134720 | `1.767871295936853e-05` | target_errors_reached | exact match |
| 13.90 | 291 | 712212480 | `4.085859321083506e-07` | target_errors_reached | exact match |
| 13.95 | 9 | 1740963840 | `5.169550218802936e-09` | max_blocks_reached | exact match |
| 14.00 | 0 | 1740963840 | zero-error upper approx. `1.720732001331271e-09` | max_blocks_reached | exact match |

The selected Fig. 4 files are:

- `results/figures/round30_fig4_h16_formal_ber.png`
- `results/figures/round30_fig4_h16_formal_ber.pdf`

Timing summary for this h16 sweep:

| metric | syndrome_lut | block_lut | ratio syndrome_lut/block_lut |
|---|---:|---:|---:|
| summed point wall-clock s | 4792.179022299941 | 4306.861681899987 | `1.1126846823150944` |
| summed decode s | 25657.941754299216 | 22908.985599386273 | `1.1199946694709428` |
| total input blocks | 1298304 | 1298304 | n/a |
| total emitted blocks | 1081920 | 1081920 | n/a |

The `13.95 dB` point has only `9` post-FEC errors and the `14.00 dB` point
has zero observed errors. They are included as observed/upper-bound evidence,
not as high-confidence floor estimates.

h15 was started as a backup and stopped after its first exact point
(`13.85 dB`, BER `6.721951314155629e-05`) once h16 became the supported Fig. 4
choice. The h10 formal MC-core partial run is retained for audit, but not used
for the selected Fig. 4 curve.

## Formal h=10 One-Hour Sweep

The original h=10 formal gate was rerun with the stated large-block parameters:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 15.2 --snr-step 0.1 --h 10 --min-post-errors 200 --max-blocks 500000 --batch-blocks 16 --seed 73010 --block-width 14 --target-post-ber 1e-9 --codec-mode batched --time-budget-s 3600 --measurement-mode mc --mc-workers 6 --accept-time-capped-min-errors 100 --output-dir results/round30_formal_h10_full_1h_20260628
```

Copied repository CSVs:

- `results/raw/round30_formal_h10_full_1h_20260628_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_formal_h10_full_1h_20260628_real_ofec_block_lut_ber.csv`
- `results/raw/round30_formal_h10_full_1h_20260628_real_ofec_curve_diff.csv`
- `results/raw/round30_formal_h10_full_1h_20260628_real_ofec_timing.csv`

Accepted rows:

| SNR Es/N0 dB | post errors | total bits | post-FEC BER / upper bound | stop | paired diff |
|---:|---:|---:|---:|---|---|
| 13.70 | 239519 | 50331648 | `0.004758814970652263` | target_errors_reached | exact match |
| 13.80 | 57500 | 50331648 | `0.001142422358194987` | target_errors_reached | exact match |
| 13.90 | 623 | 100663296 | `6.18894894917806e-06` | target_errors_reached | exact match |
| 14.00 | 0 | 1711276032 | zero-error upper approx. `1.7505839000619972e-09` | max_blocks_reached | exact match |

Generated h10 formal figure:

- `results/figures/round30_formal_h10_full_1h_ber.png`
- `results/figures/round30_formal_h10_full_1h_ber.pdf`

Timing summary for accepted rows:

| metric | syndrome_lut | block_lut | ratio syndrome_lut/block_lut |
|---|---:|---:|---:|
| summed point wall-clock s | 1223.6342593000736 | 1113.6522513995878 | `1.098757945096654` |
| summed decode s | 6110.206089695683 | 5487.470920306281 | `1.113483092381407` |
| total input blocks | 559056 | 559056 | n/a |
| total emitted blocks | 466944 | 466944 | n/a |

The formal h=10 sweep still does not yield a counted high-confidence `1e-7`
point within the one-hour budget. It reaches a counted `6.19e-6` point at
`13.9 dB`; `14.0 dB` is a zero-error max-block upper-bound point. The run
entered an in-flight `14.1 dB` point near the time boundary and was manually
stopped at about `66.5` minutes. No complete paired row or verifiable
post-error count was written for that in-flight point, so it is not reported.

## Formal h=10 Low/Mid Partial

A later formal-parameter h=10 run was started with:

```powershell
python -B -m ofec_block_lut_backend.run_real_ofec_sweep --snr-min 13.7 --snr-max 14.95 --snr-step 0.25 --h 10 --min-post-errors 200 --max-blocks 500000 --batch-blocks 16 --seed 42 --block-width 14 --codec-mode batched --target-post-ber 1e-9 --time-budget-s 1800 --point-parallel-workers 8 --output-dir results/round30_formal_h10_low_mid
```

The runner was stopped before later in-flight SNR points completed, so only the
completed paired rows are accepted. Copied repository CSVs:

- `results/raw/round30_formal_h10_low_mid_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round30_formal_h10_low_mid_real_ofec_block_lut_ber.csv`
- `results/raw/round30_formal_h10_low_mid_real_ofec_curve_diff.csv`
- `results/raw/round30_formal_h10_low_mid_real_ofec_timing.csv`

Accepted rows:

| SNR Es/N0 dB | post errors | total bits | post-FEC BER | paired diff |
|---:|---:|---:|---:|---|
| 13.70 | 508 | 49152 | 0.010335286458333334 | exact match |
| 13.95 | 348 | 49152 | 0.007080078125 | exact match |
| 14.20 | 302 | 49152 | 0.006144205729166667 | exact match |
| 14.45 | 221 | 114688 | 0.0019271414620535715 | exact match |

No interrupted in-flight SNR point is reported because no completed row with a
verifiable post-error count was written before termination.

## SNR Definition

Local OFEC uses normalized Gray-coded 16QAM with average symbol power equal to
1. The AWGN helper sets per-real-dimension noise variance to
`1 / (2 * SNR_linear)`. The Round 30 BER figure labels the axis as
`SNR Es/N0 (dB)`.

## Figures

Generated files:

- `results/figures/round30_real_ofec_ber.png`
- `results/figures/round30_real_ofec_ber.pdf`
- `results/figures/round30_real_ofec_h16_mc_ber.png`
- `results/figures/round30_real_ofec_h16_mc_ber.pdf`
- `results/figures/round30_fig4_h16_formal_ber.png`
- `results/figures/round30_fig4_h16_formal_ber.pdf`
- `results/figures/round30_formal_h10_full_1h_ber.png`
- `results/figures/round30_formal_h10_full_1h_ber.pdf`
- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`
- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`

Plot scripts:

- `scripts/plot_round30_real_ofec_ber.py`
- `scripts/plot_paper_fig2.py`
- `scripts/plot_paper_fig3.py`

Fig. 3 now uses block-width notation `w` in labels and annotations.

## High-Repeat Fig. 2/Fig. 3 Data

After the review snapshot, the fixed-map benchmarks were rerun with higher
repeat count:

```powershell
python -B -m benchmarks.bench_block_width_cache_sweep --batch-sizes 1000,10000,100000,300000 --block-widths 8,10,11,12,13,14,16,18,20 --repeats 15 --warmups 3 --max-in-memory-rows 300000 --max-timed-batch-size 300000 --max-galois-batch-size 1000 --seed 20260830 --output results/raw/block_width_cache_sweep_highrep.csv
python -B -m benchmarks.bench_fixed_map_three_backend --batch-sizes 1,10,100,1000,10000,100000,300000 --repeats 15 --warmups 3 --block-width-source results/raw/block_width_cache_sweep_highrep.csv --selection-batch-size 100000 --max-in-memory-rows 300000 --max-timed-batch-size 300000 --max-galois-batch-size 1000 --seed 20260831 --output results/raw/fixed_map_three_backend_highrep.csv
```

Outputs:

- `results/raw/block_width_cache_sweep_highrep.csv`
- `results/raw/fixed_map_three_backend_highrep.csv`

Summary:

- block-width high-repeat: 176 rows, 176 exactness pass, 164 timed;
- three-backend high-repeat: 96 rows, 96 exactness pass, 72 timed;
- repeats: `15`;
- warmups: `3`;
- timed batch sizes extend to `300000`;
- per-codeword galois timing is capped at batch `1000`.

The regenerated figures now read from these high-repeat CSVs:

```powershell
python scripts\plot_paper_fig2.py --csv results\raw\fixed_map_three_backend_highrep.csv
python scripts\plot_paper_fig3.py --csv results\raw\block_width_cache_sweep_highrep.csv
```

Fig. 3 profile batch choices:

| profile | task | plotted batch | measured peak |
|---|---|---:|---|
| BCH(255,239), r=16 | syndrome | 300000 | `w=18`, L3 |
| BCH(511,484), r=27 | syndrome | 10000 | `w=11`, L2 |

The r27 curve is substantially less jagged than the old `batch=1000` panel,
but it still has a small secondary bump around `w=13`. No smoothing or
hand-edited values were used.

## Verification

Fresh commands completed in this snapshot:

```powershell
python -B -m pytest tests/test_block_lut_backend_equivalence.py::test_point_parallel_runner_matches_serial_for_same_seed -q
python -B -m pytest tests -q
python -B -m pytest tests/test_paper_round27_plots.py -q
python -B -m pytest -q
```

Observed results:

- point-parallel regression: `1 passed, 1 warning`
- external backend tests: `8 passed, 1 warning`
- plotting smoke tests: `7 passed, 1 warning`
- full `fec_linear_backend` suite: `310 passed, 1 skipped, 27 warnings`

## Not Done

- The formal h=10 one-hour sweep did not produce a counted high-confidence
  `1e-7` point; the lowest counted accepted point is `6.19e-6`, while `14.0 dB`
  is a zero-error upper-bound point.
- No OFEC source-tree file was modified.
