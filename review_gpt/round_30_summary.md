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

## Implementation Delta

External runner update:

- `ofec_block_lut_backend/ofec_block_lut_backend/run_real_ofec_sweep.py`

The runner now supports `--point-parallel-workers`. Each worker receives a
plain backend label and constructs its backend locally:

- `syndrome_lut` -> official OFEC syndrome-LUT backend name;
- `block_lut` -> `BlockLUTBCHBackend(255, 239, block_width=14)`.

No instantiated backend object is pickled into a worker.

Test update:

- `ofec_block_lut_backend/tests/test_block_lut_backend_equivalence.py`

The added test verifies that point-parallel output matches serial output for
the same seeds.

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
waterfall region near `14.0 dB`", the current evidence points to h=18 as the
best next formal-sweep candidate:

| h | 13.9 dB evidence | 14.0 dB evidence | current interpretation |
|---:|---|---|---|
| 15 | `1.7447905106977983e-06`, `161 / 92274688` | `0 / 151912448`, zero-error upper approx. `1.97e-8` | close backup; likely slightly earlier than 14.0 for `1e-7` |
| 18 | `5.6425730387369794e-06`, `142 / 25165824` | `0 / 148979712`, zero-error upper approx. `2.01e-8` | preferred candidate; brackets the target region between 13.9 and 14.0 |
| 20 | `0 / 145375232`, zero-error upper approx. `2.06e-8` | `0 / 145375232`, zero-error upper approx. `2.06e-8` | too strong/left-shifted for the requested target |
| 22 | `0 / 142606336`, zero-error upper approx. `2.10e-8` | `0 / 142606336`, zero-error upper approx. `2.10e-8` | too strong/left-shifted for the requested target |

Additional short probes for h12/h14/h15/h16 were run by parallel subagents
under the one-hour aggregate experiment budget. All reported probe points had
more than 60 post-FEC errors, so they are recorded. However, they stopped after
only 4 to 16 measurement blocks and are startup-transient dominated. They are
smoke data only and are not used to choose h.

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
- external backend tests: `3 passed, 1 warning`
- plotting smoke tests: `5 passed, 1 warning`
- full `fec_linear_backend` suite: `308 passed, 1 skipped, 27 warnings`

## Not Done

- No final `min_post_errors=200`, `max_blocks=500000` one-hour capped sweep was
  completed. This review snapshot uses the completed `max_blocks=60000` paired
  run.
- No OFEC source-tree file was modified.
