# Latest Review Summary

Current round: Round 27 paper-figure post-processing from Round 26 CSVs.

## Goal

Produce paper-facing plots from already committed raw CSVs, without rerunning
large benchmarks:

- Fig. 2: online fixed-map speedup versus batch size.
- Fig. 3: throughput versus block width and cache fit.
- Fig. 4: decode-level decision exactness and wall-clock ratio for syndrome
  backend replacement.

Review bundle path:

- `round27_paper_figures_review_bundle.zip`

## Files Added Or Updated

Added:

- `scripts/plot_paper_fig2.py`
- `scripts/plot_paper_fig3.py`
- `scripts/plot_paper_fig4.py`
- `tests/test_paper_round27_plots.py`
- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`
- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`
- `results/figures/fig4_decode_syndrome_accel.png`
- `results/figures/fig4_decode_syndrome_accel.pdf`
- `review_gpt/round_27_summary.md`
- `round27_paper_figures_review_bundle.zip`

Updated:

- `review_gpt/latest.md`

Pre-existing uncommitted local files were left unstaged.

## Display Label Mapping

The raw CSV backend names remain unchanged. The paper plotting scripts map them
to neutral display labels:

| Raw backend | Figure display label |
|---|---|
| `PackedBatchGF2Kernel.apply_many` | `direct vectorized GF(2) matmul` |
| `PackedBlockLUTKernel.apply_many_packed` | `block-LUT (cache-aware)` |
| `galois_per_codeword` | `naive per-codeword` |

The figure titles, legends, and axis labels use the neutral display labels.

## Fig. 2

Script:

- `scripts/plot_paper_fig2.py`

Data source:

- `results/raw/fixed_map_three_backend.csv`

Figure outputs:

- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`

Data handling:

- profile: `bch_255_239_r16`
- tasks: `syndrome` and `parity`
- rows used: `timed=True` and `correctness_passed=True`
- x-axis: batch size, log scale
- y-axis: `block-LUT throughput / direct vectorized GF(2) matmul throughput`
- shaded per-iteration range: `100..100000`
- block-LUT point annotations are Mbit/s values read from the CSV
- batch `1` is kept; the plotted speedups are below `1x` there

Computed ranges from the CSV:

- syndrome: batches `1, 10, 100, 1000, 10000, 100000`; speedup range
  `0.230x..10.157x`
- parity: batches `1, 10, 100, 1000, 10000, 100000`; speedup range
  `0.263x..16.279x`

## Fig. 3

Script:

- `scripts/plot_paper_fig3.py`

Data source:

- `results/raw/block_width_cache_sweep.csv`

Figure outputs:

- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`

Data handling:

- task: `syndrome`
- representative batch: `1000` for both panels
- rows used: `timed=True` and `correctness_passed=True`
- left y-axis: measured throughput in Mbit/s
- right y-axis: theoretical block count `B=ceil(n/a)`
- background bands: `cache_level_fit` read from the CSV
- horizontal dashed line: direct vectorized GF(2) matmul throughput from the
  same profile/task/batch

Computed peaks from the CSV:

- `bch_255_239_r16`: peak at `a=14`, throughput `521.899 Mbit/s`
- `bch_511_484_r27`: peak at `a=12`, throughput `562.713 Mbit/s`

This panel shows the measured peak shifts left for the r=27 profile in this
batch, while the theoretical block count continues decreasing with larger
block width.

## Fig. 4

Script:

- `scripts/plot_paper_fig4.py`

Data source:

- `results/raw/decode_syndrome_accel.csv`

Figure outputs:

- `results/figures/fig4_decode_syndrome_accel.png`
- `results/figures/fig4_decode_syndrome_accel.pdf`

Data handling:

- rows used: `correctness_passed=True`
- left panel sums decision/status/corrected mismatch counts from the CSV
- right panel plots `Naive median_runtime_s / block-LUT median_runtime_s`

Computed values from the CSV:

- mismatch totals: decision `0`, status `0`, corrected `0`
- `bch_255_239_r16` wall-clock ratio range: `1.830x..3.703x`
- `bch_511_484_r27` wall-clock ratio range: `2.616x..6.222x`

The figure explicitly states that only the syndrome backend changes and the
error locator is unchanged.

## Data Quality Note

Known timing jitter retained for review, not plotted as a correction:

- Same nominal configuration example:
  `bch_255_239_r16`, `syndrome`, `block-LUT`, `a=12`, `batch=1000`.
- In `fixed_map_three_backend.csv`: `241.454 Mbit/s`.
- In `block_width_cache_sweep.csv`: `454.060 Mbit/s`.
- Ratio: `1.881x`.

This is treated as single-thread small-scale timing noise in the demo-scale
post-processing round. The current figures are generated from the committed
CSV rows as-is. A later high-repeat measurement round should check whether the
large-batch region settles into a stable platform.

## Not Done

- No large benchmark rerun.
- No new benchmark scale increase.
- No BER simulation or end-to-end OFEC/staircase run.
- No BER curve figure; that remains a separate future round.

## Verification

Commands run:

```bash
python -B -m pytest tests/test_paper_round27_plots.py -q
python -B scripts/plot_paper_fig2.py
python -B scripts/plot_paper_fig3.py
python -B scripts/plot_paper_fig4.py
python -B -m pytest
```

Results:

- Round 27 smoke test: `3 passed, 1 warning`
- Full test suite: `306 passed, 1 skipped, 27 warnings`

## Boundaries

- All plotted values are read from `results/raw/*.csv`.
- No manually typed throughput, speedup, or mismatch value is used inside the
  plotting scripts.
- Raw backend names are only internal CSV keys; figure display labels are
  neutralized in the plotting layer.
