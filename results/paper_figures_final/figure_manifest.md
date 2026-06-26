# Final Figure Manifest

| Figure | Source CSV | Main metric | Claim supported | Paper role | Notes |
|---|---|---|---|---|---|
| fig_cache_memory_tradeoff | cache_aware_summary.csv; long_stream_cache_width*_summary.csv | latency, LUT bytes, L2/L3 vs L1 ratio | Block width creates a cache/memory trade-off; long-stream optimum is profile dependent. | main text | Uses stream_input_bits and true stream_input_bytes; L2 mixed, L3 condition-specific. |
| fig_cache_aware_planner_oracle | cache_aware_selection_workload_summary.csv | planner/oracle ratio, oracle match rate | CacheAwarePlanner tracks measured oracle across representative workloads. | main text | Emphasizes latency ratio over exact block-width match. |
| fig_candidate_testing | candidate_testing_summary.csv | latency per candidate | PackedBlockLUT helps candidate-heavy syndrome testing. | supporting | Candidate-kernel result only, not a full Chase decoder. |
| fig_event_update_comparison | event_update_summary.csv | latency per word vs flip_count | EventUpdate reduces low-flip syndrome-update cost. | main text | Uses focused scaling data. |
| fig_component_kernel_scaling | bch_syndrome_summary.csv; component_loop_summary.csv | throughput vs total_bits/num_words | Packed kernels improve component-kernel scaling. | main text | Component-kernel evidence, not BER. |

## Old Figures Not Recommended For Main Text

- `experiment_round02_optical_workloads`: trace-level diagnostic; useful as backup only.
- `fig_planner_latency`: older dispatcher diagnostic; replaced by `fig_cache_aware_planner_oracle`.
- raw diagnostic block-width figures: replaced by `fig_cache_memory_tradeoff`.
