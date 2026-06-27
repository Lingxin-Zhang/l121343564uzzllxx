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
| Preserve component/backend exactness tests | Fresh test record in summaries: external package `5 passed, 1 warning`; main repo `310 passed, 1 skipped, 27 warnings`. | Proven at last verification |
| Produce paired real-OFEC BER evidence | `results/raw/round30_real_ofec_*`, `round30_formal_h16_mc_core_*`, `round30_formal_h18_mc_core_*`; paired diff CSVs are all zero for accepted points. | Proven for accepted points |
| Push BER as close as current run reached to `1e-7` without fabricating values | h10 review sweep reaches `1.0597088898163606e-07` at `15.95 dB` with `26 / 245350400`; summary explicitly labels it as low-error, not high-confidence. | Proven as observed point, weak for precision |
| Run formal h=10 sweep with `min_post_errors=200`, `max_blocks=500000`, broad SNR window, and one-hour cap | Current formal h10 low/mid CSV has only four completed SNRs up to `14.45 dB`; current h10 1e-7-near sweep uses `max_blocks=60000`, not `500000`. | Not complete |
| Enforce one-hour/global cap and discard low-error interrupted points | External MC runner now accepts a per-point time budget, marks capped MC points as `time_capped`, and filters time-capped pairs unless `post_fec_errors` is greater than the configured threshold. External tests and CLI smoke cover low-error discard. No formal h10 accepted time-capped row has been produced yet. | Runner support partially proven; formal use not complete |
| Later h selection around 14.0 dB | Paired MC-core h16/h18 CSVs: h16 has `188 / 67108864` at `13.9 dB`, zero observed over `671088640` bits at `14.0 dB`, paired diff zero. | Proven for h16/h18 accepted points |
| Later user request: use the suitable h value to get the best Fig. 4 | Formal h16 sweep covers `13.75` to `14.00 dB`, has six paired-exact points, includes `291` errors at `13.90 dB`, `9` errors at `13.95 dB`, and a zero-error upper bound at `14.00 dB`; figure `round30_fig4_h16_formal_ber.png/.pdf` was generated from CSV. | Proven for the updated Fig. 4 deliverable |
| Fig. 2/Fig. 3 high-repeat convergence and `a` to `w` label change | High-repeat CSVs exist; Fig. 2/Fig. 3 PNG/PDF exist; plot scripts use block width `w`. | Proven by files and plot smoke tests |
| Review bundle includes required review artifacts | Zip contains external backend/runner, scripts, tests, raw CSVs, PNG/PDF figures, and review notes. | Proven by zip entry audit |

## Current Gap

The active goal should not be marked complete yet if the original h=10 formal
requirement remains binding. The missing proof is a formal h=10 sweep with the
large `max_blocks=500000` budget and the intended broad SNR window. Current
results are useful review evidence, but they do not satisfy that specific gate.

The later h16 paired MC-core evidence and the formal h16 Fig. 4 sweep answer
the updated "put the low-BER region near 14.0 dB / use the suitable h for
Fig. 4" request, but they do not retroactively prove the original h=10 formal
sweep.

## Next Work If The Original h=10 Gate Remains Required

1. Run the formal h=10 paired sweep with the stated parameters and copy the
   accepted CSVs/figure into `results/raw` and `results/figures`.
2. Rebuild `round30_real_ofec_review_snapshot.zip`, rerun tests, and update the
   summaries with accepted/time-capped points.
