# Latest Review Summary

Current round: Round 34.

Review bundle path:

- `round34_review_bundle.zip`

## Scope

This round fills the multi-code syndrome throughput data needed for Fig. 3 and
exports three final figures from committed CSV data:

- Fig. 2 real OFEC BER overlap
- Fig. 3 multi-code three-backend syndrome throughput
- Fig. 3(b) real OFEC end-to-end decode-time comparison

No cache-miss tooling, Fig. 4 edits, paper text edits, or kernel refactors were
done.

## New Files

- `benchmarks/bench_round34_multicode_syndrome.py`
- `scripts/plot_round34_fig2_ber_overlap.py`
- `scripts/plot_round34_fig3_multicode_bars.py`
- `scripts/plot_round34_fig3b_decode_time.py`
- `tests/test_round34_artifacts.py`
- `review_gpt/round_34_summary.md`

## Data

- `results/raw/round34_multicode_three_backend_syndrome_rounds.csv`
- `results/raw/round34_multicode_three_backend_syndrome_summary.csv`
- `results/raw/round34_fig3_multicode_representative.csv`
- `results/raw/round34_fig3b_decode_time_summary.csv`

The Round34 multi-code throughput raw CSV has 1200 rows: 4 profiles x 3
backends x 10 batch sizes x 10 timing repeats. Every row passed bit-exactness
and was timed.

## Figures

- `results/figures/round34_fig2_real_ofec_ber_overlap.png`
- `results/figures/round34_fig2_real_ofec_ber_overlap.pdf`
- `results/figures/round34_fig3_multicode_three_backend.png`
- `results/figures/round34_fig3_multicode_three_backend.pdf`
- `results/figures/round34_fig3b_decode_time.png`
- `results/figures/round34_fig3b_decode_time.pdf`

The original bright block-LUT orange was changed per user request to the lower
saturation orange `#D9825B` across all three Round34 figures.

## Representative Fig. 3 Rows

Each profile uses the batch where block-LUT has the highest measured median
throughput in the Round34 scan.

| profile | representative batch | block width | naive Mbit/s | direct Mbit/s | block-LUT Mbit/s | LUT/direct | LUT/naive |
|---|---:|---:|---:|---:|---:|---:|---:|
| bch_255_239_r16 | 1500 | 14 | 5.788 | 36.177 | 558.598 | 15.441x | 96.503x |
| bch_255_231_r24 | 1000 | 20 | 5.349 | 24.900 | 534.311 | 21.458x | 99.885x |
| bch_511_484_r27 | 1500 | 16 | 10.473 | 21.508 | 460.983 | 21.433x | 44.015x |
| bch_1023_993_r30 | 1000 | 14 | 18.143 | 19.503 | 497.653 | 25.516x | 27.429x |

## Fig. 2 And Fig. 3(b)

Fig. 2 reads the existing Round31 real OFEC BER CSVs and gates on
`round31_fig4_real_ofec_curve_diff.csv`; all 10 SNR points have
`post_fec_errors_delta=0` and `post_fec_ber_delta=0.0`.

Fig. 3(b) uses total `decode_sec` over the same 10 SNR points:

- reference syndrome backend: `19072.019 s`
- block-LUT backend: `17142.423 s`
- ratio recorded in summary only: `1.113x`

## Verification

- `python -m pytest tests/test_round34_artifacts.py -q`: passed during
  development
- `python -m pytest -q`: 327 passed, 1 skipped, 27 warnings
