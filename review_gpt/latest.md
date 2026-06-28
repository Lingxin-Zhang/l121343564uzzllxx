# Latest Review Summary

Current round: Round 32.

Review bundle path:

- `round32_review_bundle.zip`

## Scope

Round 32 refreshes the paper-figure artifacts without rerunning real OFEC
simulation:

- Fig. 2: BER overlap from existing R31 CSVs plus a decode-time inset.
- Fig. 3: absolute throughput vs batch, multi-round anti-noise rerun.
- Fig. 4: block width vs cache, multi-round throughput plus cache-fit fallback
  panel because hardware cache-miss counters are unavailable on this Windows
  host.

The OFEC BER curve and decode-time inset reuse existing committed R31 data.
No true OFEC simulation was rerun.

## Added Files

Benchmarks:

- `benchmarks/bench_round32_cache_probe.py`
- `benchmarks/bench_round32_fixed_map_antinoisy.py`
- `benchmarks/bench_round32_width_antinoisy.py`
- `benchmarks/round32_common.py`

Plot scripts:

- `scripts/plot_round32_fig2_ber_inset.py`
- `scripts/plot_round32_fig3_throughput.py`
- `scripts/plot_round32_fig4_cache_width.py`
- `scripts/plot_round32_same_tier_proxy.py`

Test:

- `tests/test_round32_artifacts.py`

Dependency metadata:

- `requirements.txt` now lists `pandas>=1.5`, used by the new aggregation and
  plotting scripts.

## Counter Probe

Read-only counter probe result:

- `perf`: not found
- `taskset`: not found
- `/proc/sys/kernel/perf_event_paranoid`: not found
- Windows `typeperf`: found, but it exposes system counters, not a Linux
  `perf_event_open`-style way to wrap the LUT kernel.

Therefore Fig. 4(b) is emitted as `cache_fit_fallback` and does not contain
fabricated L1/L2/LLC miss rates. Miss-rate fields are blank.

Counter/fallback CSV:

- `results/raw/round32_cache_counter_probe.csv`

The fallback still verifies that cache-fit boundaries are batch independent:
for each profile and width, the cache level is identical at batch `100`,
`1000`, and `100000`, as expected from table size being independent of batch.

## Fig. 2

Outputs:

- `results/figures/round32_fig2_ber_decode_inset.png`
- `results/figures/round32_fig2_ber_decode_inset.pdf`

Inputs:

- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

Result:

- paired BER rows: `10`
- mismatch count: `0`
- aggregated decode-time ratio: `1.1125625601918068x`
- per-point decode-time ratio range: `1.018156381027306x` to
  `1.1923112775917915x`

The `13.95 dB` point remains the existing low-event open-marker tail point.
The excluded `14.00 dB` zero-error upper-bound point is not plotted.

## Fig. 3

Outputs:

- `results/figures/round32_fig3_throughput.png`
- `results/figures/round32_fig3_throughput.pdf`
- `results/figures/round32_fig3_throughput_min.png`
- `results/figures/round32_fig3_throughput_min.pdf`
- `results/figures/round32_fig3_throughput_envelope.png`
- `results/figures/round32_fig3_throughput_envelope.pdf`
- `results/figures/round32_fig3_throughput_scatter.png`
- `results/figures/round32_fig3_throughput_scatter.pdf`

CSV:

- `results/raw/round32_fig3_throughput_rounds.csv`
- `results/raw/round32_fig3_throughput_summary.csv`
- `results/raw/round32_fig3_speedup_summary.csv`
- raw source traces:
  - `results/raw/round32_fig3_throughput_rounds_worker.csv`
  - `results/raw/round32_fig3_throughput_rounds_main.csv`

The plot uses absolute throughput. It does not use a speedup y-axis.

Median LUT/direct ratios from `round32_fig3_speedup_summary.csv`:

| task | batch | LUT Mbit/s | direct Mbit/s | LUT/direct |
|---|---:|---:|---:|---:|
| syndrome | 1000 | 589.731685 | 43.561171 | 13.538013 |
| syndrome | 100000 | 271.392371 | 44.844492 | 6.051855 |
| parity | 1000 | 631.343567 | 45.651635 | 13.829594 |
| parity | 100000 | 271.903099 | 44.812819 | 6.067529 |

The batch-1000 spike is still visible, but the figure now reports min, median,
max envelope, and all-round scatter instead of hiding the spread. The worker
trace was more stable than the main fallback trace at parity batch 100/1000.

## Fig. 4

Outputs:

- `results/figures/round32_fig4_cache_width.png`
- `results/figures/round32_fig4_cache_width.pdf`
- `results/figures/round32_fig4_cache_width_min.png`
- `results/figures/round32_fig4_cache_width_min.pdf`
- `results/figures/round32_fig4_cache_width_envelope.png`
- `results/figures/round32_fig4_cache_width_envelope.pdf`
- `results/figures/round32_fig4_cache_width_selected_r16_r24.png`
- `results/figures/round32_fig4_cache_width_selected_r16_r24.pdf`
- `results/figures/round32_fig4_cache_width_scatter.png`
- `results/figures/round32_fig4_cache_width_scatter.pdf`

CSV:

- `results/raw/round32_width_throughput_rounds.csv`
- `results/raw/round32_width_throughput_summary.csv`
- `results/raw/round32_cache_width_decision_summary.csv`
- raw source traces:
  - `results/raw/round32_width_throughput_r16_r24.csv`
  - `results/raw/round32_width_throughput_r16_r24_main.csv`
  - `results/raw/round32_width_throughput_r27_r30.csv`

Best median widths:

| profile | best w | median Mbit/s | CV | cache fit |
|---|---:|---:|---:|---|
| BCH(255,239), r16 | 14 | 621.034225 | 0.026576 | L2 |
| BCH(255,231), r24 | 20 | 582.016468 | 0.083610 | DRAM |
| BCH(511,484), r27 | 16 | 631.334383 | 0.100321 | L3 |
| BCH(1023,993), r30 | 14 | 626.857452 | 0.054965 | L3 |

The selected paper-facing panel is the r16/r24 version because those were the
priority codes and r16 shows the cleanest cache-boundary alignment. The r24
best width moved into the DRAM-fit band in this run, so it is reported as data,
not forced into an L2-boundary story.

## Same-Tier Control

CSV:

- `results/raw/round32_same_tier_dram_pressure_proxy.csv`
- `results/raw/round32_same_tier_summary.csv`

Figure:

- `results/figures/round32_same_tier_dram_pressure_proxy.png`
- `results/figures/round32_same_tier_dram_pressure_proxy.pdf`

This is a read-only cache-pressure proxy, not a true hardware guarantee that
every table lookup is served from DRAM. It did not become monotone:

- BCH(255,239), natural: non-monotone
- BCH(255,239), pressure proxy: non-monotone
- BCH(255,231), natural: non-monotone
- BCH(255,231), pressure proxy: non-monotone

Therefore it is kept as a diagnostic control and should not be used as evidence
for the stronger "same-tier DRAM makes timing monotone" claim.

## Noise Handling

All Round32 timing rows record:

- `round_index`
- probe loop timings
- raw and probe-normalized throughput columns

CSV:

- `results/raw/round32_noise_normalization_summary.csv`

The probe normalization is a software frequency proxy. It is useful for
diagnostics but does not fully remove Python/thermal scheduling noise.

Affinity:

- Fig. 4 r16/r24 worker: `psutil cpu_affinity set to 2`
- Fig. 4 r27/r30: `psutil cpu_affinity set to 4`
- Fig. 3 main trace: `psutil cpu_affinity set to 6`

Windows did not expose a Linux-style P/E-core proof path. The summary reports
affinity setting rather than claiming confirmed P-core residency.

## Parallelism And Timing

Subagent split:

- Beauvoir: Fig. 4 r16/r24 cache-fit fallback and width sweep.
- Harvey: Fig. 3 throughput rerun.
- Main agent: Fig. 2 inset, r27/r30 lightweight Fig. 4 supplement, proxy
  control, merge/plot/test/docs.

Observed experiment durations:

- Fig. 4 r16/r24 cache probe: `0.280 s`
- Fig. 4 r16/r24 width worker: `20.174 s`
- Fig. 3 worker: `365.136 s`
- Fig. 3 main fallback trace: about `273.5 s`
- Fig. 4 r27/r30 supplement: about `15.4 s`
- same-tier pressure proxy: about `40.8 s`

No command hit the 1-hour per-process cap, and the total experiment time stayed
under the 3-hour round cap.

## Verification

Round32 smoke:

- `python -B -m pytest tests/test_round32_artifacts.py -q`
- result: `4 passed, 1 warning`

Full suite:

- `python -B -m pytest tests -q`
- result: `318 passed, 1 skipped, 27 warnings`
