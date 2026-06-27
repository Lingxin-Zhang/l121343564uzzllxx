# Round 30 Completion Audit

This audit checks the current repository state against the original Round 30
objective file and the later h-calibration updates. It is intentionally stricter
than the review summary: an item is marked complete only when current files or
command output directly prove it.

## Evidence Inspected

- Goal objective:
  `C:\Users\25798\.codex\attachments\9504d22f-81bf-48e3-b8b0-900f6dbaf832\goal-objective.md`
- Main repository files and committed Round 30 artifacts
- External package:
  `D:\PKU\acp2026\ofec_block_lut_backend`
- Review bundle:
  `round30_real_ofec_review_snapshot.zip`
- Main review notes:
  `review_gpt/latest.md`,
  `review_gpt/round_30_summary.md`

## Requirement Status

| Requirement | Current evidence | Status |
|---|---|---|
| Keep OFEC source tree read-only | External changes are in `ofec_block_lut_backend`; review notes state no OFEC source edits. | Proven for submitted artifacts |
| Fix injected backend parallelization without pickling instantiated backend objects | `ofec_block_lut_backend/run_real_ofec_sweep.py` constructs backends inside workers; external tests cover point-parallel and MC-mode equivalence. | Proven for external runner |
| Verify parallel does not change BER results on a small gate | `review_gpt/round_30_summary.md` records serial vs point-parallel gate: 3/3 rows identical. | Proven by recorded gate |
| Preserve component/backend exactness tests | Fresh test record in summaries: external package `8 passed, 1 warning`; main repo `310 passed, 1 skipped, 27 warnings`. | Proven at last verification |
| Produce paired real-OFEC BER evidence | `results/raw/round30_real_ofec_*`, `round30_formal_h16_mc_core_*`, `round30_formal_h18_mc_core_*`, and `round30_formal_h10_full_1h_20260628_*`; paired diff CSVs are all zero for accepted points. | Proven for accepted points |
| Push BER as close as current run reached to `1e-7` without fabricating values | h10 review sweep reaches `1.0597088898163606e-07` at `15.95 dB` with `26 / 245350400`; summary explicitly labels it as low-error, not high-confidence. | Proven as observed point, weak for precision |
| Run formal h=10 sweep with `min_post_errors=200`, `max_blocks=500000`, broad SNR window, and one-hour cap | `results/raw/round30_formal_h10_full_1h_20260628_*` covers `SNR=13.7..15.2` command settings and accepted paired rows through `14.0 dB`; all accepted rows have paired diff zero. It reached a counted `6.19e-6` point at `13.9 dB` and a zero-error upper-bound point at `14.0 dB`, but not a counted high-confidence `1e-7` point. | Proven as executed; precision limit documented |
| Enforce one-hour/global cap and discard low-error interrupted points | External MC runner accepts a per-point time budget and filters time-capped pairs below the error threshold. In the formal h10 run, an in-flight `14.1 dB` point had no complete paired row or verifiable post-error count when the process was manually stopped at about `66.5` minutes, so it was not reported. | Proven for accepted-row filtering; hard-stop granularity caveat documented |
| Later h selection around 14.0 dB | Paired MC-core h16/h18 CSVs: h16 has `188 / 67108864` at `13.9 dB`, zero observed over `671088640` bits at `14.0 dB`, paired diff zero. | Proven for h16/h18 accepted points |
| Later user request: use the suitable h value to get the best Fig. 4 | Formal h16 sweep covers `13.75` to `14.00 dB`, has six paired-exact points, includes `291` errors at `13.90 dB`, `9` errors at `13.95 dB`, and a zero-error upper bound at `14.00 dB`; figure `round30_fig4_h16_formal_ber.png/.pdf` was generated from CSV. | Proven for the updated Fig. 4 deliverable |
| Fig. 2/Fig. 3 high-repeat convergence and `a` to `w` label change | High-repeat CSVs exist; Fig. 2/Fig. 3 PNG/PDF exist; plot scripts use block width `w`. Review notes explicitly caveat that r27 is less jagged but still has a small secondary bump around `w=13`. | Proven by files and plot smoke tests |
| Review bundle includes required review artifacts | Zip contains external backend/runner, scripts, tests, raw CSVs, PNG/PDF figures, and review notes. | Proven by zip entry audit |

## Current Gap

The original h=10 formal sweep gate has now been executed with the stated
large `max_blocks=500000` and broad SNR-window settings. The remaining
scientific limitation is not a missing run, but the outcome of that run: within
the one-hour budget it did not produce a counted high-confidence `1e-7` point.
The accepted h=10 evidence is a counted `6.19e-6` point at `13.9 dB` plus a
zero-error upper-bound point at `14.0 dB`.

The time-cap implementation has coarse MC-wave granularity. The formal h10 run
entered an in-flight `14.1 dB` point near the time boundary and was manually
stopped after about `66.5` minutes. Because no complete paired row or
verifiable post-error count was written for that in-flight point, it was
discarded rather than estimated.

## Remaining Cautions

1. Do not describe the h=10 formal curve as high-confidence `1e-7` evidence.
2. Do not describe r27 Fig. 3 as fully smoothed; it remains measured data with
   a documented small secondary bump.
