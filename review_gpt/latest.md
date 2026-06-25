# Latest Review Summary

Current round: round 19, local reference repository paths.

## Goal

Record two local reference repository locations in `AGENTS.md` so future rounds
can inspect local clones instead of repeatedly searching the web.

## Modified Files

- `AGENTS.md`
- `review_gpt/latest.md`
- `review_gpt/round_19_summary.md`

## Implementation Notes

- Added a `Local Reference Repository Paths` section to `AGENTS.md`.
- Recorded `D:\PKU\OFEC\project\ofec-huawei-github` as the local
  OFEC/Huawei-style reference clone.
- Recorded `D:\PKU\OFEC\project\Chase-Pyndiah-demo` as the local
  Chase-Pyndiah demo clone.
- Confirmed both paths exist locally.
- Confirmed observed remotes:
  - `ofec-huawei-github`: `https://github.com/Lingxin-Zhang/OFEC_CNN.git`
  - `Chase-Pyndiah-demo`: `https://github.com/kit-cel/Chase-Pyndiah-demo.git`
- Kept clean-room constraints: local repositories may be inspected for
  parameters, calling patterns, and workload design implications, but external
  implementation code must not be copied into this repository.

## Tests

- `python -m pytest -q`
  - Result: `249 passed, 1 skipped, 16 warnings`

## Known Issues

- This round did not inspect the contents of the local reference repositories.
  It only recorded the local paths and verified that the directories exist.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains an unrelated
  untracked file and was not staged for this round.

## Next Steps

- For the immediate workload-trace and BCH/eBCH component-kernel work, the two
  local repositories should be enough as primary local references.
- If later work needs independent BCH algebra cross-checks, consider adding
  local clones or installed references for Linux BCH, `python-bchlib`, AFF3CT,
  or a pinned `galois` environment. These are optional until a concrete
  cross-check task needs them.
