# Round 28 Summary: M2 End-to-End BER Smoke Simulator

## Scope

Round 28 adds a new, independent M2 product-code BER simulator under
`D:\PKU\acp2026\m2_ofec_sim`. It is not added as source code inside
`fec_linear_backend`, because `AGENTS.md` says the GF(2) kernel repository must
not host BER simulations or full decoder runs. The source and raw outputs are
packaged in the review bundle:

- `round28_m2_ofec_sim_review_bundle.zip`

## Reference Study

The local OFEC driver `reproduce_fig3_baseline.py` builds an OFEC codec context
from `OFECConfig`, `EBCH256_239`, `OFECSingleEncoder`, and
`OFECSingleWindowedHIHODecoder`.

Parameter interpretation:

- `h`: hard-decision iteration/stage count. The local decoder window scale is
  `10*h + 1`.
- `min-post-errors`: stop a point after this many post-FEC bit errors are
  accumulated.
- `max-blocks`: stop a point when this many emitted blocks have been measured,
  even if the error target has not been reached.
- `batch-blocks`: outer-loop batch size for generated output blocks.
- `seed`: base seed; the script offsets by SNR index.

The local implementation is faster than a naive Python loop because it uses
batched encode/decode paths, a dense EBCH syndrome-LUT backend, windowed
measurement phases, and optional parallel execution modes. The Huawei reference
tree is a compiled AFF3CT-style C++ codebase with templated codec modules and
performance-oriented monitor/decoder infrastructure. M2 only uses these repos
to understand conventions and timing structure; it does not copy their decoder
implementation.

## M2 Design

M2 is a minimal product-code simulator:

- component code: BCH(255,239), `r=16`
- matrix source:
  `make_bch255_t2_syndrome_matrix_galois_systematic()`
- product-code block: `255 x 255`
- encoding: row parity from `uP`, then column parity with the same component
  code
- channel: normalized 16-QAM AWGN hard decision
- decoding: `h` row/column BDD sweeps
- error location: existing `BDDLUTDecoder` syndrome-to-position LUT, shared
  between both curves
- reference syndrome backend: direct vectorized GF(2) matrix multiply via
  `PackedBatchGF2Kernel.apply_many`
- block-LUT syndrome backend: `PackedBlockLUTKernel.apply_many_packed` with
  `block_width=14`

Thus the two M2 curves differ only in the component syndrome linear map backend.

## Generated CSVs

Inside the bundle:

- `m2_ofec_sim/results/raw/m2_reference_ber.csv`
- `m2_ofec_sim/results/raw/m2_block_lut_ber.csv`
- `m2_ofec_sim/results/raw/m2_curve_diff.csv`
- `m2_ofec_sim/results/raw/m2_timing.csv`

## Command

```bash
python -B -m m2_ofec_sim.cli --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 10 --batch-blocks 1 --seed 42 --block-width 14 --time-budget-s 1800 --output-dir results/raw
```

## End-to-End Equality Result

`m2_curve_diff.csv` reports exact equality at every completed SNR point:

| SNR dB | matched | pre error delta | post error delta | post BER delta |
|---:|---|---:|---:|---:|
| 13.7 | True | 0 | 0 | 0.0 |
| 13.8 | True | 0 | 0 | 0.0 |
| 13.9 | True | 0 | 0 | 0.0 |
| 14.0 | True | 0 | 0 | 0.0 |
| 14.1 | True | 0 | 0 | 0.0 |
| 14.2 | True | 0 | 0 | 0.0 |

This is the new evidence from this round: after installing the block-LUT
syndrome backend into a full product-code generate/channel/decode/statistics
chain, the BER-vs-SNR outputs are unchanged point by point for the smoke run.

## Timing Result

From `m2_timing.csv`:

| backend | points | total init s | online s | total s |
|---|---:|---:|---:|---:|
| reference | 6 | 2.624756700010039 | 0.3521323000313714 | 2.9768890000414103 |
| block_lut | 6 | 2.6270003999234177 | 0.15540809993399307 | 2.782408499857411 |

Total elapsed ratio, reference/block-LUT:

- `1.0698964584797546x`

Online decode/channel simulation ratio, reference/block-LUT:

- `2.265858x`

The short run is dominated by one-time BCH matrix and LUT construction, so the
online timing is the more relevant number for future longer sweeps.

## BER Rows

Reference and block-LUT BER rows are identical. The shared values are:

| SNR dB | blocks | pre errors | post errors | post BER |
|---:|---:|---:|---:|---:|
| 13.7 | 1 | 770 | 819 | 0.01259515570934256 |
| 13.8 | 1 | 669 | 541 | 0.008319876970396002 |
| 13.9 | 1 | 640 | 437 | 0.006720492118415994 |
| 14.0 | 1 | 591 | 278 | 0.004275278738946559 |
| 14.1 | 1 | 604 | 336 | 0.00516724336793541 |
| 14.2 | 3 | 1581 | 145 | 0.0007433038574907087 |

The nonmonotonic smoke-scale values are retained as measured. This round does
not claim a converged BER curve.

## 30 Minute Budget

The run did not time out. It finished in roughly three seconds including
initialization, so no partial-stop recovery was needed.

Observed online time per product-code block:

- reference: `0.04401653750392143 s/block`
- block-LUT: `0.019426012491749134 s/block`

Counting estimate for future runs, assuming 100 post errors are needed and
65025 coded bits per product block:

| target BER | blocks | reference online | block-LUT online |
|---:|---:|---:|---:|
| 1e-6 | 1538 | 1.1283 min | 0.4980 min |
| 1e-7 | 15379 | 11.2822 min | 4.9792 min |
| 1e-8 | 153788 | 112.8203 min | 49.7915 min |

This is a wall-clock planning estimate only.

## Verification

Commands run:

```bash
python -B -m pytest tests -q
python -B -m m2_ofec_sim.cli --snr-min 13.7 --snr-max 14.2 --snr-step 0.1 --h 10 --min-post-errors 100 --max-blocks 10 --batch-blocks 1 --seed 42 --block-width 14 --time-budget-s 1800 --output-dir results/raw
python -B -m pytest
```

Results:

- M2 smoke test: `1 passed`
- BER sweep: `points=6 matched=True reference_over_block_lut=1.0699`
- `fec_linear_backend` full test suite: `306 passed, 1 skipped, 27 warnings`

## Not Done

- No low-floor BER run.
- No h=15 production-scale reproduction.
- No BER figure generation.
- No integration into local `ofec-0.1.0`.
- No GF(2) kernel changes.
