# Final Experiment Artifact Index

This document is the review entry point for the consolidated paper-facing
artifacts. It records which results can support which claims, which figures are
recommended for a short paper, and which boundaries should remain explicit.

## Final Artifact Map

| Paper claim / figure purpose | Main artifact | Supporting CSV/summary | Figure/table output | Status |
|---|---|---|---|---|
| Component-decoder exactness | `results/summary/component_decoder_exactness_summary.csv` | `results/raw/component_decoder_exactness.csv` | `results/summary/final_exactness_table.csv` | paper main result |
| Candidate-heavy syndrome/candidate testing | `results/summary/candidate_testing_summary.csv` | `results/raw/candidate_testing.csv` | `results/paper_figures_final/fig_candidate_testing.*` | paper supporting result |
| CacheAwarePlanner vs measured oracle | `results/summary/cache_aware_selection_workload_summary.csv` | `results/raw/cache_aware_selection.csv` | `results/paper_figures_final/fig_cache_aware_planner_oracle.*` | paper main result |
| Cache/memory/block-width trade-off | `results/summary/cache_aware_summary.csv` | `results/raw/cache_aware.csv` | `results/paper_figures_final/fig_cache_memory_tradeoff.*` | paper main result |
| Long-stream L1/L2/L3 cache-width diagnostic | `results/summary/long_stream_cache_width_replication_summary.csv` | `results/summary/long_stream_cache_width_summary.csv`; `results/raw/long_stream_cache_width*.csv` | Panel C of `fig_cache_memory_tradeoff.*` | paper supporting result |
| BCH syndrome throughput | `results/summary/bch_syndrome_summary.csv` | `results/raw/bch_syndrome.csv` | Panel A of `fig_component_kernel_scaling.*` | paper supporting result |
| Component loop scaling | `results/summary/component_loop_summary.csv` | `results/raw/component_loop.csv` | Panel B of `fig_component_kernel_scaling.*` | paper supporting result |
| Event-update low-flip update | `results/summary/event_update_summary.csv` | `results/raw/event_update.csv` | `results/paper_figures_final/fig_event_update_comparison.*` | paper main/supporting result |
| Optical trace workload | `results/summary/optical_workloads_summary.csv` | `results/raw/optical_workloads.csv`; `results/summary/optical_workload_breakdown_summary.csv` | no final main figure in this round | appendix / backup result |
| Hardware / reproducibility metadata | `results/raw/hardware_profile.json`; `results/raw/artifact_provenance.json` | git commit metadata | provenance JSON | reproducibility metadata |

## Final Figure Shortlist

Recommended main-text package:

1. `results/summary/final_exactness_table.csv` plus `results/summary/final_representative_table.csv`.
2. `fig_cache_memory_tradeoff`: cache-aware LUT block-width latency, footprint, and long-stream cache-tier sensitivity.
3. `fig_cache_aware_planner_oracle`: planner/oracle latency ratio and oracle match rates.
4. `fig_component_kernel_scaling`: BCH syndrome stream and component-loop scaling.
5. Either `fig_event_update_comparison` or `fig_candidate_testing`, depending on the final story emphasis.

Recommended supporting or appendix material:

- `fig_candidate_testing`: useful for candidate-heavy syndrome workloads.
- `fig_event_update_comparison`: useful for low-flip syndrome updates.
- Optical trace workload summaries: keep as trace-level kernel evidence, not as a full decoder result.

Not recommended as final main-text figures:

- Old diagnostic block-width, density, batch, and stream figures.
- Older planner comparison figures that do not use the cache-aware oracle calibration summary.
- Round 2 exploratory figures whose notes mark them as diagnostic or lightweight.

## Claim Audit

| Claim | Supporting file | Supporting fields / metrics | Recommended paper wording | Currently holds? | Notes |
|---|---|---|---|---|---|
| GF(2) backends are bit-exact | `tests/test_correctness.py`; result summaries with correctness fields | `correctness_passed`; `correctness_all_true` | Accelerated GF(2) kernels are validated against a naive matrix-vector reference on the tested matrices and workloads. | yes | Kernel-level claim only. |
| Component-decoder decisions are exact in the tested component model | `component_decoder_exactness_summary.csv` | `exact_mismatch_count=0`; `correctness_all_true=True`; `all_double_bit_errors` | The component decision path preserves decoded word, correction mask, and status over full double-error coverage. | yes | Not a BER or full decoder claim. |
| PackedBlockLUT accelerates candidate-heavy syndrome computation | `candidate_testing_summary.csv` | `mean_latency_per_candidate_us`; `correctness_all_true` | Packed LUT evaluation reduces per-candidate syndrome cost for candidate-heavy batches while preserving exact outputs. | yes | In 26/32 representative full-preset candidate-test groups, PackedBlockLUT is fastest. |
| EventUpdate accelerates low-flip syndrome updates | `event_update_summary.csv` | `flip_count`; `relative_to_from_scratch_packed` | Incremental update avoids full recomputation for low-flip updates. | yes | flip=1 shows about 21.45x versus packed from-scratch in the focused summary; benefit shrinks as flips increase. |
| CacheAwarePlanner closely tracks measured oracle on major workloads | `cache_aware_selection_workload_summary.csv` | `mean_planner_over_oracle`; `p90_planner_over_oracle`; match rates | The cache-footprint-guided planner stays close to the measured oracle across representative workloads. | yes | Paper preset mean over five workloads is about 1.041; do not claim theoretical optimality. |
| Block width creates a latency-memory/cache trade-off | `cache_aware_summary.csv`; `long_stream_cache_width*_summary.csv` | `block_width`; `lut_bytes`; cache fit fields; latency | The best LUT block width depends on LUT footprint and the cache tier reached by the table. | yes | Profile-specific wording is required. |
| Long-stream cache-width behavior is profile/workload dependent | `long_stream_cache_width_summary.csv`; `long_stream_cache_width_replication_summary.csv` | `best_cache_level`; `best_l2_over_best_l1`; `best_l3_over_best_l1` | Long-stream measurements show profile-dependent preferred cache tiers. | yes | BCH replication favors L1; eBCH-like replication favors L3. |
| eBCH-like long-stream workload shows condition-specific L3 advantage | `long_stream_cache_width_replication_summary.csv` | `l3_strong_20x_claim=True`; `best_l3_over_best_l1=0.649321` | In the tested eBCH-like long-stream regime, an L3-fitting width passes the stable 20% gate against the best L1-fitting width. | condition-specific | Only for the tested eBCH-like condition. |
| L2 evidence remains mixed and should not be written as stable strong claim | `long_stream_cache_width_replication_summary.csv` | `l2_strong_20x_claim`; profile-specific ratios | L2-fitting widths are promising in selected eBCH-like runs, but evidence is mixed across profiles. | mixed | BCH replication has L1 best and no L2/L3 strong claim. |
| Optical trace workload is trace-level kernel-call evidence, not full decoder | `optical_workloads_summary.csv` | `executed_*`; `aggregate_latency_per_executed_unit_us` | Trace-level workloads exercise component-kernel call patterns representative of optical-FEC processing. | supporting | Do not write end-to-end decoder or BER conclusions. |
| Method is decision-preserving / BER-neutral by exact replacement, not BER-improving | `final_exactness_table.csv`; exactness summaries | `exact_mismatch_count=0`; `correctness_all_true=True` | The acceleration replaces exact GF(2) component-kernel computations and is decision-preserving for the tested component model. | yes | Do not claim BER improvement. |

## Paper-Ready Wording Snippets

### CacheAwarePlanner

The proposed cache-footprint-guided planner closely tracks the measured oracle across representative GF(2) kernel workloads. On the paper preset, the mean planner/oracle latency ratio is about 1.041 across sparse single-word, dense batch, candidate-test, component-decode, and event-update workloads. The planner is intentionally workload-aware: it uses cache footprint, output mode, batch size, and update structure to select a backend and block width rather than relying on a single globally fixed implementation.

### Exactness

All accelerated component-kernel decisions are checked against reference outputs in the tested component model. For the full double-error sweep, `all_double_bit_errors` covers 32385 received words and all tested syndrome backend variants report `exact_mismatch_count=0`. The exactness table also checks decoded word equality, correction-mask equality, and status equality, supporting a decision-preserving replacement claim for this component path.

### Candidate / Event / Component Kernel

PackedBlockLUT is particularly effective for candidate-heavy syndrome testing because each candidate can reuse compact precomputed XOR contributions. In the full-preset candidate-test summaries, PackedBlockLUT is the fastest backend in 26 of 32 representative candidate-test groups. EventUpdate addresses a complementary low-flip regime: when the current syndrome is already available, updating only the flipped positions is substantially cheaper than recomputing from scratch for small flip counts. The BCH syndrome and component-loop summaries provide the broader component-kernel scaling evidence.

### Cache / Memory / Long-Stream Block Width

Block width controls a direct latency-memory trade-off: wider LUT blocks reduce online XOR work but increase table footprint and change which cache tier can hold the table. The long-stream cache-width results show that the best tier is profile dependent. BCH(255,239)-like replication still favors an L1-fitting width, while the tested eBCH-like long-stream condition shows a condition-specific L3-fitting advantage. These results support cache-aware selection rather than a universal L1, L2, or L3 rule.

## Subagent Inputs Integrated

- Result/claim audit subagent: identified safe claim boundaries, recommended final table sources, and highlighted that `best_backend_by_workload.csv` should remain diagnostic.
- Figure-design subagent: identified the final figure set, recommended replacing old diagnostic figures with cache-aware oracle and long-stream-aware figures, and warned against using old planner or trace plots as main-text evidence.
