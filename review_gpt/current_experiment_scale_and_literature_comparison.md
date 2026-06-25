# Current Experiment Scale and Literature Comparison Report

This report summarizes the current benchmark settings in the repository and
compares them with the experimental design style observed in the local paper
materials under `paper/`. It is intended for GPT review and planning only. No
new benchmark was run for this report.

## Scope of This Read-Only Check

Checked repository-side materials:

- `benchmarks/`
- `scripts/summarize_results.py`
- `scripts/export_paper_figures.py`
- `scripts/plot_results.py`
- `results/raw/*.csv`
- `results/summary/*.csv`
- `paper/notes/experiment_plan.md`
- `paper/notes/acp_writing_style_notes.md`
- `paper/references/summaries/*.md`
- selected local PDFs under `paper/references/papers/`
- selected ACP style examples under `paper/references/style_examples/`

Skills / capabilities used:

- `pdf`: used to inspect local PDF materials.
- `paper-figures-advise`: used for figure-design perspective.
- Local CSV/script inspection: used to extract actual current benchmark
  settings.

## Current Code / Matrix Profiles

The project currently evaluates fixed GF(2) linear kernels on these main code
profiles:

| profile | shape | source/status | role |
|---|---:|---|---|
| `bch_255_239_r16` | `n=255, r=16` | `galois_systematic_candidate`, verified candidate | main BCH-like component profile |
| `ebch_256_239_r17` | `n=256, r=17` | extended candidate, not fully verified | eBCH-like candidate |
| `synthetic_bch_like_127_r14` | `n=127, r=14` | deterministic synthetic | smaller scaling point |
| `synthetic_511_r32` | `n=511, r=32` | deterministic synthetic | larger packed-output scaling point |

Most result files are currently generated with the lightweight preset. The
largest regular batch/candidate size is `4096`; the largest component-loop
input is `65536` component words; the stream and BCH syndrome benchmarks use
`total_bits = 1,000,000` and `10,000,000`.

## Current Benchmark Settings

### Basic Microbenchmarks

| CSV | rows | main variables | scale |
|---|---:|---|---|
| `block_width.csv` | 36 | `block_width=4,6,8,10,12,14,16,18,20`; backends `Naive`, `SparseXor`, `BlockLUT`, `PackedBlockLUT`; `density=0.05` | small single-axis LUT sweep |
| `density.csv` | 30 | densities `0.005,0.01,0.02,0.05,0.1,0.5`; backends `Naive`, `SparseXor`, `BlockLUT`, `PackedBlockLUT`, `PackedBatch`; `batch_size=1024`, `block_width=8` | moderate density sweep |
| `batch.csv` | 35 | batch sizes `1,4,16,64,256,1024,4096`; five backend modes; `density=0.05`, `block_width=8` | moderate batch sweep |
| `stream.csv` | 18 | `total_bits=1e6,1e7`; `iterations=1,5,10`; three backends | largest bit-count stream test; still CPU microbenchmark |

Default repeats:

- `block_width`, `density`, `batch`: `5`
- `stream`: `3`

### BCH / Component-Oriented Benchmarks

| CSV | rows | main variables | scale |
|---|---:|---|---|
| `bch_syndrome.csv` | 48 | matrix sources `placeholder`, `galois_systematic_candidate`; `total_bits=1e6,1e7`; `iterations=1,5,10`; four backends | component syndrome throughput at up to about `39215` words per iteration |
| `component_loop.csv` | 36 | `num_words=4096,16384,65536`; `iterations=1,5,10`; four backends | repeated component-loop simulation, up to `655360` component-word operations per timed call |
| `event_update.csv` | 36 | `flip_count=1,2,4,8`; `batch_size=4096`; `iterations=1,5,10`; three update/from-scratch methods | event-update workload, fixed batch size |
| `planner.csv` | 144 | workload types `batch_syndrome`, `event_update`; densities `0.005,0.05,0.5`; batch sizes `1,16,64,4096`; flip counts `1,2,4` | HybridPlanner v1 diagnostic |

Default repeats:

- `bch_syndrome`, `component_loop`, `event_update`, `planner`: `3`

### Round 2 / Round 6 Cache and Profile Benchmarks

| CSV | rows | main variables | scale |
|---|---:|---|---|
| `cache_aware.csv` | 972 | code profiles `bch_255_239_r16`, `ebch_256_239_r17`, `synthetic_511_r32`; block widths `4..20 step 2`; batch sizes `1,64,4096`; densities `0.005,0.05,0.5`; four backends | broadest current microbenchmark grid |
| `code_profile_scaling.csv` | 48 | four code profiles; batch sizes `1,64,4096`; `density=0.05`; `block_width=8`; four backends | code-size scaling, but only one block width and one density |
| `cache_aware_selection.csv` | 153 | three code profiles; three cache profiles; workloads `sparse_single`, `dense_batch`, `candidate_test_packed`, `component_decode_batch`, `event_update`; batch sizes `1,64,1024,4096`; block widths `4,6,8,10` | planner-vs-oracle diagnostic; lightweight repeats are `1` |

Important limitation:

- `cache_aware_selection.csv` is useful for logic and correctness, but its
  lightweight timing has only one repeat by default, so it should not be used
  as a final performance claim without a heavier preset.

### Candidate / Optical-Trace / Exactness Benchmarks

| CSV | rows | main variables | scale |
|---|---:|---|---|
| `candidate_testing.csv` | 210 | code profiles `bch_255_239_r16`, `ebch_256_239_r17`, `synthetic_511_r32`; pattern types `chase_ii_all`, `fixed_weight`; weights `1,2,4,8`; counts `256,4096`; seven backends/methods | candidate-pattern kernel only; not full Chase/GRAND decoder |
| `optical_workloads.csv` | 160 | workload types `product_like`, `staircase_like`, `ofec_like`; code profiles `bch_255_239_r16`, `ebch_256_239_r17`; `num_blocks=8,32`; `window_len=4,8`; `iterations=1,3`; batch cap `64` | trace-level kernel-call workload, not a full decoder |
| `optical_workload_breakdown.csv` | 320 | breakdown by task kind and backend/method | explains intended/executed counts |
| `component_decoder_exactness.csv` | 24 | cases `all_zero`, `all_single_bit_errors`, `sampled_double_bit_errors`, `sampled_triple_bit_errors`, `random_error_batch`, `random_received_batch`; one main code profile | correctness/exactness, not a speed benchmark |

Exactness scale details:

- `all_single_bit_errors`: all 255 single-bit errors.
- `sampled_double_bit_errors`: 4096 sampled double-bit errors in lightweight.
- possible double-bit errors for `n=255`: `255*254/2 = 32385`.
- random batches: `1024` or `4096` depending on case/preset.

## How Large Are the Current Experiments?

The current experiments are best described as lightweight-to-moderate
CPU microbenchmarks:

- Smallest scale: single-vector or batch size `1`.
- Common batch scale: `64`, `1024`, `4096`.
- Largest component-loop scale: `65536` component words over up to `10`
  iterations.
- Largest stream/BCH-syndrome scale: `10,000,000` input bits, or about `39215`
  BCH(255)-length component words per iteration.
- Code widths: mostly `r=16` and `r=17`, with one synthetic `r=32` scaling
  profile.
- Repeats: usually `3` or `5`, but cache-aware selection lightweight uses `1`.
- Timing level: Python/NumPy wall-clock runtime, not cycles, hardware area,
  power, pJ/bit, or BER/NCG simulation.

This is a reasonable development-stage benchmark suite, but it is not yet at
the scale or methodological strength usually expected for a final optical-FEC
implementation paper claim.

## What Similar Papers Usually Measure

Based on the local paper summaries and selected PDF text extraction:

### Smith et al. 2012 Staircase Codes

Typical design:

- Focuses on full FEC code behavior for 100-Gb/s OTN.
- Reports BER / output error rate and NCG, including very low target error
  rates such as `1e-15`.
- Uses staircase/product-like structure and BCH component codes.
- Discusses decoder iteration and implementation complexity.

Implication for this project:

- A kernel paper does not need to reproduce full BER curves if it only changes
  exact kernels, but it should clearly show bit-exact decoder output
  equivalence and explain why BER/NCG is unchanged by construction.

### Fougstedt et al. 2017 BCH Decoder

Typical design:

- Treats BCH decoder implementation itself as a first-class optical
  interconnect/FEC problem.
- Uses hardware synthesis context, including a 28-nm CMOS process.
- Compares latency and energy/bit, and discusses syndrome-table versus
  algebraic decoder approaches.

Implication for this project:

- The closest software analogue is to report latency, throughput, memory
  footprint, and exactness for BCH component kernels.
- If no hardware is built, do not imitate area/power claims; instead report
  memory/cache footprint and wall-clock runtime carefully.

### Fougstedt et al. 2018 / 2019 Staircase and Product-Like Decoder Hardware

Typical design:

- Reports high-throughput decoder implementations, often around Tb/s-class
  information throughput.
- Uses realistic BCH component codes, e.g. `BCH(511,484,3)` and
  `BCH(511,475,4)` in the staircase decoder paper.
- Includes area/power breakdowns, memory behavior, window size, iteration count,
  and switching-activity-based evaluation.
- Emphasizes that memory movement and scheduling can dominate practical
  efficiency.

Implication for this project:

- Current experiments cover memory/cache footprint, but only for small
  software tables and Python-level runtime.
- Adding more realistic code profiles such as `n=511,r≈27/36` or BCH
  `t=3/4` syndrome widths would better match the literature.
- A useful paper figure should include a memory/latency trade-off, not only
  speed curves.

### Zokaei et al. 2022 Open FEC Encoder

Typical design:

- Focuses on Open FEC / oFEC encoder memory organization.
- Uses eBCH-like component length `256` with `239` information bits and `17`
  parity bits.
- Reports power/memory/area improvements in hardware.

Implication for this project:

- `ebch_256_239_r17` is an important profile to keep.
- For a software kernel paper, memory footprint and cache-aware LUT selection
  are the right analogues to hardware memory optimization.

### Rapp et al. 2024 Optimized OFEC/Staircase Decoding

Typical design:

- Uses BER curves and decoding-iteration settings.
- Compares algorithmic variants over OFEC/staircase workloads.
- Evaluates complexity/performance trade-offs, not just a single timing point.

Implication for this project:

- Candidate-testing and planner workloads should be framed as kernel-call
  acceleration for exact simulation, not as a new decoder.
- If candidate testing remains in the paper, it needs stronger workload
  semantics and multiple candidate-count regimes.

### ACP / Short-Conference Style Examples

Typical design:

- 4-page papers often use 2-3 figures and 1-2 tables.
- FEC implementation examples combine architecture/setup figures with BER,
  throughput, latency, or hardware-resource tables.
- They present fewer experiments than JLT papers, but each figure is tightly
  connected to the main claim.

Implication for this project:

- The final paper should not show every current CSV as a separate figure.
- It should select 2-3 high-signal figures and 1 compact table:
  - architecture / backend selection diagram
  - latency-memory/cache trade-off
  - workload-regime comparison or planner-vs-oracle summary
  - bit-exact correctness table

## Main Gap Between Current Experiments and Paper-Style Experiments

1. Current settings are mostly lightweight.
   - Many grids use batch sizes up to `4096`, but repeats are only `3-5`, and
     cache-aware selection uses repeat `1`.
   - This is fine for development, but final claims need stronger repeats,
     confidence intervals, and possibly larger batches.

2. Code-profile realism is mixed.
   - `bch_255_239_r16` and `ebch_256_239_r17` are useful.
   - `synthetic_511_r32` is only a synthetic scaling profile.
   - Similar hardware papers often evaluate real BCH component configurations
     such as `BCH(511,484,3)` or `BCH(511,475,4)`.

3. Current figures are still more diagnostic than paper-like.
   - They show latency/throughput but often with one fixed density or one fixed
     block width.
   - More paper-like plots should combine latency, throughput, memory footprint,
     and regime boundaries.

4. System-level relevance is approximate.
   - `optical_workloads.csv` is a trace-level kernel-call workload, not a full
     product/staircase/oFEC decoder.
   - This should be described honestly unless a full decoder simulation is
     later added.

5. No BER/NCG or power/area data.
   - That is acceptable if the paper is framed as exact kernel acceleration,
     but then the correctness/equivalence evidence must be very strong.
   - The paper should not claim BER improvement or hardware energy improvement.

6. Some useful dimensions are sparse.
   - `code_profile_scaling.csv` uses only one density and one block width.
   - `density.csv` uses one batch size and one block width.
   - `batch.csv` uses one density and one block width.
   - This makes each figure easy to read, but weakens regime-map claims.

## Recommended Paper-Level Experiment Design

### Experiment 1: Latency-Memory Trade-Off for LUT Block Width

- Purpose: show the cache/memory trade-off of BlockLUT / PackedBlockLUT.
- X-axis: `block_width`.
- Y-axis left: latency per component word.
- Y-axis right or second panel: LUT table bytes.
- Backends: `Naive`, `SparseXor`, `PackedBatch`, `PackedBlockLUT`.
- Code profiles: `bch_255_239_r16`, `ebch_256_239_r17`, and one larger BCH-like
  or synthetic profile.
- Suggested points: block width `4,6,8,10,12,14,16,18,20`.
- Suggested repeats: at least `7-15`.
- Figure style: two-panel line plot with error bars; avoid using this as a
  standalone speedup claim.

### Experiment 2: Density and Batch Regime Map

- Purpose: show when SparseXor, PackedBlockLUT, and PackedBatch each wins.
- X-axis: density.
- Y-axis: batch size.
- Cell color: best backend or normalized latency to oracle.
- Backends: `SparseXor`, `PackedBlockLUT`, `PackedBatch`, `Naive`.
- Code profile: start with `bch_255_239_r16`, then repeat for `ebch_256_239_r17`.
- Suggested density points: `0.001,0.002,0.005,0.01,0.02,0.05,0.1,0.25,0.5`.
- Suggested batch points: `1,4,16,64,256,1024,4096,16384`.
- Suggested repeats: `7`.
- Figure style: heatmap or faceted heatmaps.

### Experiment 3: BCH/eBCH Component Syndrome Throughput

- Purpose: anchor the work in the BCH/eBCH component syndrome workload.
- X-axis: total processed bits or component words.
- Y-axis: throughput in Mword/s or Mbit/s.
- Backends: `Naive`, `PackedBatch`, `PackedBlockLUT`, optionally planner.
- Matrix sources: `galois_systematic_candidate`, `ebch_256_239_r17`.
- Suggested total bits: `1e6, 3e6, 1e7, 3e7, 1e8` if runtime permits.
- Suggested repeats: `5-7`.
- Figure style: log-x line plot with error bars.

### Experiment 4: Component Loop Scaling

- Purpose: show repeated component-loop workload, closer to full decoder
  structure than a single kernel call.
- X-axis: `num_words * iterations`.
- Y-axis: throughput or wall-clock runtime.
- Backends: same as syndrome benchmark.
- Suggested num_words: `4096,16384,65536,262144`.
- Suggested iterations: `1,3,5,10`.
- Figure style: line plot or grouped bars; use one panel per backend group.

### Experiment 5: Event-Update Flip Count Sweep

- Purpose: show incremental update advantage when only a few positions change.
- X-axis: `flip_count`.
- Y-axis: latency per update.
- Backends/methods: from-scratch `PackedBlockLUT`, `EventUpdate.loop_update`,
  `EventUpdate.update_many`.
- Flip counts: `1,2,4,8,16,32`.
- Batch sizes: `64,1024,4096,16384`.
- Figure style: log-y or normalized speedup plot with exactness note.

### Experiment 6: Cache-Aware Planner vs Oracle

- Purpose: show whether planner choices track measured best backend.
- X-axis: workload regime or code profile.
- Y-axis: planner/oracle latency ratio.
- Backends: selected backend as color or marker.
- Inputs: `cache_aware_selection.csv`.
- Suggested repeats: current lightweight repeat `1` should be replaced by at
  least `5-7`.
- Figure style: grouped bar or boxplot; add a horizontal line at `1.0`.

### Experiment 7: Bit-Exact Correctness Table

- Purpose: defend the central claim that outputs are unchanged.
- Rows: syndrome/parity, candidate patterns, component decoder exactness,
  event update.
- Columns: profile, number of checked words/patterns, mismatch count, status.
- Include current facts:
  - all single-bit errors checked for `n=255`.
  - 4096 sampled double-bit errors in lightweight.
  - full double-bit enumeration is possible as a full preset if run.

## Suggested Final Figure/Table Set for a 4-Page ACP Paper

Recommended minimum:

1. Fig. 1: backend architecture and planner flow.
2. Fig. 2: block-width latency-memory trade-off.
3. Fig. 3: workload-regime comparison, either heatmap or compact grouped plot.
4. Table I: speed/latency/memory summary for representative profiles.
5. Table II or a short subtable: bit-exact correctness evidence.

If space is tight, merge Table II into Table I and keep only three figures.

## Short Answer to "Are Current Experiments Large Enough?"

Current experiments are sufficient for:

- correctness development,
- backend debugging,
- initial microbenchmark trends,
- showing that cache-aware selection can be measured,
- generating preliminary figures for internal review.

Current experiments are not yet sufficient for:

- strong paper-level speedup claims,
- stable planner-over-oracle claims,
- full optical-FEC system claims,
- BER/NCG claims,
- hardware energy/area claims.

The most important upgrades before paper submission are:

1. replace lightweight one-repeat planner timing with repeat `7+`;
2. add larger batch/stream sizes where runtime permits;
3. add or justify more realistic BCH/eBCH profiles beyond synthetic `511_r32`;
4. produce one regime-map figure instead of many isolated one-axis plots;
5. include a compact correctness table that clearly separates sampled and full
   enumeration cases.

## Notes for GPT Review

- Do not interpret current `optical_workloads.csv` as a full product/staircase
  or OFEC decoder benchmark.
- Do not interpret current `cache_aware_selection.csv` as final performance
  evidence because lightweight repeat count is `1`.
- Do not claim BER, NCG, pJ/bit, FPGA area, or ASIC power.
- The current strongest evidence is bit-exact correctness plus Python-level
  runtime trends for fixed GF(2) kernels.
- The literature comparison supports the paper framing as implementation /
  simulation-runtime acceleration, but the final experiments should be more
  selective and stronger than the current diagnostic suite.
