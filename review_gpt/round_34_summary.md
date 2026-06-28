# Round 34 Summary

## Scope

Round 34 completed three tasks:

1. Measured the missing four-code, three-backend BCH syndrome throughput data
   for Fig. 3.
2. Exported final Fig. 2, Fig. 3, and Fig. 3(b) PNG/PDF artifacts.
3. Preserved raw per-repeat timing rows and wrote review-ready summaries.

No existing kernel was refactored. No cache-miss tools, GPU tools, Fig. 4 edits,
or paper text edits were used.

## Data Sources

New Round34 throughput data:

- `results/raw/round34_multicode_three_backend_syndrome_rounds.csv`
- `results/raw/round34_multicode_three_backend_syndrome_summary.csv`
- `results/raw/round34_fig3_multicode_representative.csv`

Existing Round31 real OFEC data reused for plotting:

- `results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_block_lut_ber.csv`
- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

Derived decode-time summary:

- `results/raw/round34_fig3b_decode_time_summary.csv`

## Benchmark Protocol

Benchmark script:

- `benchmarks/bench_round34_multicode_syndrome.py`

Profiles:

- `bch_255_239_r16`
- `bch_255_231_r24`
- `bch_511_484_r27`
- `bch_1023_993_r30`

Task:

- syndrome only, `v H^T`

Backends:

- `galois_per_codeword`
- `PackedBatchGF2Kernel.apply_many`
- `PackedBlockLUTKernel.apply_many_packed`

Batch scan:

- `100, 300, 500, 700, 1000, 1500, 2000, 3000, 5000, 10000`

Repeats and warmups:

- `repeats=10`
- `warmups=30`

The raw CSV has one row per repeat. Final row count is 1200, matching 4
profiles x 3 backends x 10 batch sizes x 10 repeats. Every row has
`correctness_passed=True` and `timed=True`.

CPU affinity:

- `psutil cpu_affinity set to 2`

Time limits:

- The benchmark completed in about 5.3 minutes.
- The 20-minute single-process cap and 40-minute round cap were not triggered.

Block widths:

- `bch_255_239_r16`: `w=14`, fixed per round request
- `bch_255_231_r24`: `w=20`, from `round32_cache_width_decision_summary.csv`
- `bch_511_484_r27`: `w=16`, from `round32_cache_width_decision_summary.csv`
- `bch_1023_993_r30`: `w=14`, from `round32_cache_width_decision_summary.csv`

## Fig. 3 Representative Rows

Each code uses the batch where block-LUT had the highest measured median
throughput in the Round34 scan.

| profile | representative batch | block width | backend | throughput Mbit/s | CV |
|---|---:|---:|---|---:|---:|
| bch_255_239_r16 | 1500 |  | galois_per_codeword | 5.788412 | 0.028207 |
| bch_255_239_r16 | 1500 |  | PackedBatchGF2Kernel.apply_many | 36.177226 | 0.073750 |
| bch_255_239_r16 | 1500 | 14 | PackedBlockLUTKernel.apply_many_packed | 558.598001 | 0.173149 |
| bch_255_231_r24 | 1000 |  | galois_per_codeword | 5.349259 | 0.104997 |
| bch_255_231_r24 | 1000 |  | PackedBatchGF2Kernel.apply_many | 24.900034 | 0.143248 |
| bch_255_231_r24 | 1000 | 20 | PackedBlockLUTKernel.apply_many_packed | 534.311130 | 0.330934 |
| bch_511_484_r27 | 1500 |  | galois_per_codeword | 10.473207 | 0.027478 |
| bch_511_484_r27 | 1500 |  | PackedBatchGF2Kernel.apply_many | 21.508001 | 0.076219 |
| bch_511_484_r27 | 1500 | 16 | PackedBlockLUTKernel.apply_many_packed | 460.983302 | 0.060989 |
| bch_1023_993_r30 | 1000 |  | galois_per_codeword | 18.143236 | 0.017987 |
| bch_1023_993_r30 | 1000 |  | PackedBatchGF2Kernel.apply_many | 19.503397 | 0.029700 |
| bch_1023_993_r30 | 1000 | 14 | PackedBlockLUTKernel.apply_many_packed | 497.652812 | 0.182670 |

Ratios:

| profile | block-LUT / direct | block-LUT / naive |
|---|---:|---:|
| bch_255_239_r16 | 15.441x | 96.503x |
| bch_255_231_r24 | 21.458x | 99.885x |
| bch_511_484_r27 | 21.433x | 44.015x |
| bch_1023_993_r30 | 25.516x | 27.429x |

## Figures

Plot scripts:

- `scripts/plot_round34_fig2_ber_overlap.py`
- `scripts/plot_round34_fig3_multicode_bars.py`
- `scripts/plot_round34_fig3b_decode_time.py`

Figure outputs:

- `results/figures/round34_fig2_real_ofec_ber_overlap.png`
- `results/figures/round34_fig2_real_ofec_ber_overlap.pdf`
- `results/figures/round34_fig3_multicode_three_backend.png`
- `results/figures/round34_fig3_multicode_three_backend.pdf`
- `results/figures/round34_fig3b_decode_time.png`
- `results/figures/round34_fig3b_decode_time.pdf`

The block-LUT color was changed from the original bright orange to the lower
saturation orange `#D9825B` after visual review.

Legend placement was visually checked after export; legends do not cover
curves, points, bars, or annotations.

## Fig. 2 BER Exactness

The BER overlap plot reads the existing Round31 real OFEC CSVs:

- reference backend: `round31_fig4_real_ofec_syndrome_lut_ber.csv`
- block-LUT backend: `round31_fig4_real_ofec_block_lut_ber.csv`

The diff gate reads:

- `results/raw/round31_fig4_real_ofec_curve_diff.csv`

All 10 SNR points from 13.50 dB to 13.95 dB have:

- `matched=True`
- `post_fec_errors_delta=0`
- `post_fec_ber_delta=0.0`

## Fig. 3(b) Decode Time

Fig. 3(b) uses total `decode_sec` over the 10 shared Round31 SNR points.

| backend | total decode_sec |
|---|---:|
| reference syndrome backend | 19072.018519 |
| block-LUT backend | 17142.423448 |

The ratio is `1.112563x` and is recorded here only; the figure itself does not
annotate a ratio.

## Verification

Commands run:

- `python -m pytest tests/test_round34_artifacts.py -q`
- `python -m benchmarks.bench_round34_multicode_syndrome --profiles 255_239 --batch-sizes 100 --repeats 2 --warmups 1 --time-budget-s 120 --output results/raw/_round34_smoke_rounds.csv --summary-output results/raw/_round34_smoke_summary.csv`
- `python -m benchmarks.bench_round34_multicode_syndrome --profiles 255_239,255_231,511_484,1023_993 --batch-sizes 100,300,500,700,1000,1500,2000,3000,5000,10000 --repeats 10 --warmups 30 --cpu-core 2 --time-budget-s 1200 --output results/raw/round34_multicode_three_backend_syndrome_rounds.csv --summary-output results/raw/round34_multicode_three_backend_syndrome_summary.csv`
- `python scripts/plot_round34_fig3_multicode_bars.py`
- `python scripts/plot_round34_fig2_ber_overlap.py`
- `python scripts/plot_round34_fig3b_decode_time.py`

The temporary smoke CSVs were removed after the real run.

Final verification:

- `python -m pytest -q`: 327 passed, 1 skipped, 27 warnings

## Review Bundle

Bundle path:

- `round34_review_bundle.zip`
