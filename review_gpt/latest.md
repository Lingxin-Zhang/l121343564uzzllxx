# Latest Review Summary

Current round: Round 33 continuation.

Review bundle path:

- `round33_review_bundle.zip`

## Scope

This round only refreshes Fig. 3: fixed-width `w=14` block-LUT throughput versus
batch for BCH(255,239), r16. It does not touch Fig. 2, Fig. 4, OFEC, decoder, or
BER artifacts.

## Main Files

- `benchmarks/bench_round33_fig3_dense_batch.py`
- `scripts/plot_round33_fig3_dense_batch.py`
- `tests/test_round33_fig3.py`
- `review_gpt/round_33_summary.md`

## Data And Figures

Merged CSVs:

- `results/raw/round33_fig3_throughput_all.csv`
- `results/raw/round33_fig3_stage_breakdown_all.csv`
- `results/raw/round33_fig3_throughput_summary.csv`
- `results/raw/round33_fig3_speedup_summary.csv`

Figures:

- `results/figures/round33_fig3_dense_batch.png`
- `results/figures/round33_fig3_dense_batch.pdf`
- `results/figures/round33_fig3_dense_batch_median.png`
- `results/figures/round33_fig3_dense_batch_median.pdf`
- `results/figures/round33_fig3_dense_batch_envelope.png`
- `results/figures/round33_fig3_dense_batch_envelope.pdf`
- `results/figures/round33_fig3_scatter.png`
- `results/figures/round33_fig3_scatter.pdf`
- `results/figures/round33_fig3_stage_breakdown.png`
- `results/figures/round33_fig3_stage_breakdown.pdf`

## Execution

The benchmark now writes CSV rows incrementally by default. This was added
because earlier full shards A/B/C and F were stopped before their end-of-run CSV
write and produced no usable output.

Final merged throughput:

- 1224 timed rows
- 1224 correctness-passed rows
- batch `10` through `100000`: 10 rounds
- batch `300000`: 1 round, bulk and fixed-chunk streaming
- batch `1000000` and `3000000`: 1 round, bulk and fixed-chunk streaming

All post-incremental shards completed without hitting their watchdogs.

## Result

The data does not support the stronger claim that `batch ~= 1000` is a proven
L1-fit peak.

- syndrome bulk best LUT throughput: batch `1500`, `545.887 Mbit/s`,
  `15.560x` versus direct
- syndrome bulk best ratio: batch `2000`, `15.624x`
- parity bulk best LUT throughput and best ratio: batch `2000`,
  `564.382 Mbit/s`, `15.953x`
- no measured bulk batch through `3000000` shows direct vectorized GF(2) matmul
  overtaking block-LUT
- high-batch fixed-chunk streaming through `3000000` also keeps block-LUT ahead,
  but only as single-round extension evidence

Recommended conservative paper fill-in `[N]` from fixed-chunk streaming rows:

- syndrome: about `14.3x` to `15.3x`
- parity: about `14.7x` to `15.6x`
- shorthand if one value is required: about `15x`, with the ranges and absolute
  Mbit/s values reported alongside it

Stage timing is index-dominated across the sweep, and read/prepare plus XOR do
not show a sharp special minimum at batch `1000`. The safe diagnosis is a
small/mid-batch plateau with later degradation, not a narrow L1-residency peak.

## Verification

- `python -B -m pytest tests/test_round33_fig3.py -q`: 6 passed
- `python -B -m pytest tests -q`: 324 passed, 1 skipped, 27 warnings

## Push Status

The continuation commit was created locally. Initial push attempts failed due
to transient GitHub connectivity from this host:

- attempt 1: `Recv failure: Connection was reset`
- attempt 2: `Could not resolve host: github.com`
- attempt 3: `RPC failed; curl 55 Recv failure: Connection was reset`
- attempt 4: `Failed to connect to github.com port 443`
- attempt 5: `Could not resolve host: github.com`
- attempt 6: `git -c http.version=HTTP/1.1 push` succeeded

Final push succeeded with HTTP/1.1.
