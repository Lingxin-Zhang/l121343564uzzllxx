# Round 27 Summary: Paper Figure Post-Processing

## Scope

This round converts Round 26 raw CSV data into three paper-facing figures:

- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`
- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`
- `results/figures/fig4_decode_syndrome_accel.png`
- `results/figures/fig4_decode_syndrome_accel.pdf`

Scripts:

- `scripts/plot_paper_fig2.py`
- `scripts/plot_paper_fig3.py`
- `scripts/plot_paper_fig4.py`

Smoke test:

- `tests/test_paper_round27_plots.py`

Review bundle:

- `round27_paper_figures_review_bundle.zip`

No large benchmark was rerun.

## Neutral Figure Labels

The plotting layer maps raw backend keys to neutral labels:

| Raw backend | Figure label |
|---|---|
| `PackedBatchGF2Kernel.apply_many` | `direct vectorized GF(2) matmul` |
| `PackedBlockLUTKernel.apply_many_packed` | `block-LUT (cache-aware)` |
| `galois_per_codeword` | `naive per-codeword` |

This is a plotting-only rename. The raw CSV backend columns are unchanged.

## Fig. 2

Script:

- `scripts/plot_paper_fig2.py`

Input CSV:

- `results/raw/fixed_map_three_backend.csv`

Output:

- `results/figures/fig2_fixed_map_speedup.png`
- `results/figures/fig2_fixed_map_speedup.pdf`

The script filters `bch_255_239_r16`, `timed=True`, and
`correctness_passed=True`, then computes the plotted y-value as:

```text
block-LUT throughput / direct vectorized GF(2) matmul throughput
```

The figure includes syndrome and parity panels, keeps batch `1`, shades
`100..100000`, and annotates block-LUT Mbit/s from the CSV.

CSV-derived ranges:

- syndrome speedup: `0.230x..10.157x`
- parity speedup: `0.263x..16.279x`

## Fig. 3

Script:

- `scripts/plot_paper_fig3.py`

Input CSV:

- `results/raw/block_width_cache_sweep.csv`

Output:

- `results/figures/fig3_block_width_cache_sweep.png`
- `results/figures/fig3_block_width_cache_sweep.pdf`

The script uses syndrome rows at representative batch `1000`, with
`timed=True` and `correctness_passed=True`. It plots measured Mbit/s on the
left y-axis and `B=ceil(n/a)` on the right y-axis. Cache background bands are
read from `cache_level_fit`.

CSV-derived peaks:

- `bch_255_239_r16`: peak at `a=14`, `521.899 Mbit/s`
- `bch_511_484_r27`: peak at `a=12`, `562.713 Mbit/s`

## Fig. 4

Script:

- `scripts/plot_paper_fig4.py`

Input CSV:

- `results/raw/decode_syndrome_accel.csv`

Output:

- `results/figures/fig4_decode_syndrome_accel.png`
- `results/figures/fig4_decode_syndrome_accel.pdf`

The left panel reports mismatch totals from the CSV:

- decision: `0`
- status: `0`
- corrected: `0`

The right panel computes:

```text
Naive median_runtime_s / block-LUT median_runtime_s
```

CSV-derived wall-clock ratio ranges:

- `bch_255_239_r16`: `1.830x..3.703x`
- `bch_511_484_r27`: `2.616x..6.222x`

Only the syndrome backend changes in this benchmark; the error locator is
unchanged.

## Data Quality Note

Known timing jitter retained for review:

- Configuration:
  `bch_255_239_r16`, syndrome, block-LUT, `a=12`, `batch=1000`.
- `fixed_map_three_backend.csv`: `241.454 Mbit/s`.
- `block_width_cache_sweep.csv`: `454.060 Mbit/s`.
- Cross-benchmark ratio: `1.881x`.

This round does not repair the jitter by rerunning. It records the issue and
leaves high-repeat convergence checks to a later measurement round.

## Not Done

- No new benchmark scale.
- No end-to-end BER or OFEC/staircase run.
- No BER curve figure.

## Verification Status

Completed before this summary was written:

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
