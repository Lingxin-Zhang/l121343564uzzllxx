# Round 32 Summary: Anti-Noise Figures And Counter Fallback

## Boundary

This round does not rerun real OFEC simulation. Fig. 2 is generated from
existing R31 BER/timing CSVs. The new work is restricted to kernel benchmark
runners, plotting scripts, review notes, and generated review artifacts.

Review bundle:

- `round32_review_bundle.zip`

## Counter Availability

Read-only probe:

- `perf`: unavailable
- `taskset`: unavailable
- `/proc/sys/kernel/perf_event_paranoid`: unavailable
- Windows `typeperf`: available, but not suitable for wrapping the LUT kernel
  as Linux `perf_event_open` would.

Consequence:

- Fig. 4(b) uses `counter_mode=cache_fit_fallback`.
- L1/L2/LLC miss-rate columns are blank, not zero.
- The cache-fit fallback shows deterministic layer transitions and batch
  invariance, but it is not a hardware cache-miss measurement.

## Fig. 2: BER With Decode-Time Inset

Script:

- `scripts/plot_round32_fig2_ber_inset.py`

Outputs:

- `results/figures/round32_fig2_ber_decode_inset.png`
- `results/figures/round32_fig2_ber_decode_inset.pdf`

Data:

- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

Result:

- `0` mismatches across `10` paired BER points.
- Decode-time aggregate ratio: `1.1125625601918068x`.
- Per-point decode ratio range: `1.018156381027306x` to
  `1.1923112775917915x`.

No real OFEC point was rerun.

## Fig. 3: Throughput Vs Batch

Script:

- `scripts/plot_round32_fig3_throughput.py`

Raw CSVs:

- `results/raw/round32_fig3_throughput_rounds_worker.csv`
- `results/raw/round32_fig3_throughput_rounds_main.csv`
- merged: `results/raw/round32_fig3_throughput_rounds.csv`

Summary CSVs:

- `results/raw/round32_fig3_throughput_summary.csv`
- `results/raw/round32_fig3_speedup_summary.csv`

Figures:

- `results/figures/round32_fig3_throughput.png`
- `results/figures/round32_fig3_throughput_min.png`
- `results/figures/round32_fig3_throughput_envelope.png`
- `results/figures/round32_fig3_throughput_scatter.png`
- PDF versions for each.

Median LUT/direct ratios:

| task | batch | LUT/direct | LUT Mbit/s | direct Mbit/s |
|---|---:|---:|---:|---:|
| syndrome | 1000 | 13.538013 | 589.731685 | 43.561171 |
| syndrome | 100000 | 6.051855 | 271.392371 | 44.844492 |
| parity | 1000 | 13.829594 | 631.343567 | 45.651635 |
| parity | 100000 | 6.067529 | 271.903099 | 44.812819 |

The batch-1000 point remains a peak in the median view. This round makes the
noise explicit with min, max-envelope, and scatter views rather than hiding the
spread.

## Fig. 4: Block Width And Cache

Scripts:

- `benchmarks/bench_round32_cache_probe.py`
- `benchmarks/bench_round32_width_antinoisy.py`
- `scripts/plot_round32_fig4_cache_width.py`

Raw CSVs:

- `results/raw/round32_cache_counter_probe_r16_r24.csv`
- `results/raw/round32_cache_counter_probe_r27_r30.csv`
- merged: `results/raw/round32_cache_counter_probe.csv`
- `results/raw/round32_width_throughput_r16_r24.csv`
- `results/raw/round32_width_throughput_r16_r24_main.csv`
- `results/raw/round32_width_throughput_r27_r30.csv`
- merged: `results/raw/round32_width_throughput_rounds.csv`

Summary CSV:

- `results/raw/round32_width_throughput_summary.csv`
- `results/raw/round32_cache_width_decision_summary.csv`

Figures:

- `results/figures/round32_fig4_cache_width.png`
- `results/figures/round32_fig4_cache_width_min.png`
- `results/figures/round32_fig4_cache_width_envelope.png`
- `results/figures/round32_fig4_cache_width_selected_r16_r24.png`
- `results/figures/round32_fig4_cache_width_scatter.png`
- PDF versions for each.

Best median widths:

| profile | best w | median Mbit/s | CV | cache fit |
|---|---:|---:|---:|---|
| BCH(255,239), r16 | 14 | 621.034225 | 0.026576 | L2 |
| BCH(255,231), r24 | 20 | 582.016468 | 0.083610 | DRAM |
| BCH(511,484), r27 | 16 | 631.334383 | 0.100321 | L3 |
| BCH(1023,993), r30 | 14 | 626.857452 | 0.054965 | L3 |

Cache-fit boundaries from the fallback table:

| profile | L1 w | L2 w | L3 w | DRAM w |
|---|---|---|---|---|
| BCH(255,239), r16 | 4-9 | 10-14 | 15-19 | 20-26 |
| BCH(255,231), r24 | 4-8 | 9-14 | 15-18 | 19-26 |
| BCH(511,484), r27 | 4-6 | 7-12 | 13-17 | 18-24 |
| BCH(1023,993), r30 | 4-5 | 6-11 | 12-16 | 17-24 |

Interpretation:

- r16 aligns with the L2 upper boundary (`w=14`).
- r24, r27, and r30 do not all align to an L2 boundary in this Windows run;
  those outcomes are reported as observed data, not forced into a stronger
  cache-boundary claim.
- The deterministic cache-fit fallback confirms layer transitions and
  batch-invariance, but cannot replace real hardware miss counters.

## Same-Tier Pressure Proxy

Script:

- `scripts/plot_round32_same_tier_proxy.py`

CSV:

- `results/raw/round32_same_tier_dram_pressure_proxy.csv`
- `results/raw/round32_same_tier_summary.csv`

Figures:

- `results/figures/round32_same_tier_dram_pressure_proxy.png`
- `results/figures/round32_same_tier_dram_pressure_proxy.pdf`

Result:

- The proxy did not produce monotone timing in either natural or
  cache-flushed mode for r16/r24.
- It is not a true same-tier DRAM proof and should remain diagnostic only.

## Noise And Affinity

CSV:

- `results/raw/round32_noise_normalization_summary.csv`

Each timing row records software probe timings and raw/normalized throughput.
The probe is a coarse frequency proxy, not a hardware frequency lock. It does
not fully remove noise.

Affinity status:

- r16/r24 Fig. 4 worker used `psutil cpu_affinity set to 2`.
- r27/r30 Fig. 4 supplement used `psutil cpu_affinity set to 4`.
- Fig. 3 main trace used `psutil cpu_affinity set to 6`.

Windows did not provide a Linux `sched_getcpu()` / `/proc` proof path here, so
the run reports affinity setting rather than confirmed P-core residency.

## Parallel Split

Subagents:

- Beauvoir: r16/r24 cache fallback and width sweep.
- Harvey: Fig. 3 throughput worker.

Main agent:

- Fig. 2 inset.
- r27/r30 lightweight Fig. 4 supplement.
- Fig. 3 fallback trace.
- same-tier proxy.
- merge, plot, test, package, commit, push.

No experiment process exceeded 1 hour. Total experiment wall time stayed under
3 hours.

## Verification

Round32 smoke:

```powershell
python -B -m pytest tests/test_round32_artifacts.py -q
```

Full suite:

```powershell
python -B -m pytest tests -q
```

Results are added after the verification commands complete.

Recorded results:

- Round32 smoke: `4 passed, 1 warning`
- Full suite: `318 passed, 1 skipped, 27 warnings`
