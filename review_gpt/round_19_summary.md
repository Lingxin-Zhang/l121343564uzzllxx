# Round 19 Summary

## Goal

Record local reference repository paths in `AGENTS.md` for future reference
inspection.

## Modified Files

- `AGENTS.md`
- `review_gpt/latest.md`
- `review_gpt/round_19_summary.md`

## Changes

- Added local path for the OFEC/Huawei-style reference clone:
  `D:\PKU\OFEC\project\ofec-huawei-github`.
- Added local path for the Chase-Pyndiah demo clone:
  `D:\PKU\OFEC\project\Chase-Pyndiah-demo`.
- Documented observed git remotes for both local clones.
- Preserved the rule that external repositories are clean-room references only
  and must not be copied into this repository.

## Verification

- Confirmed both local directories exist.
- Ran `python -m pytest -q`.
- Result: `249 passed, 1 skipped, 16 warnings`.

## Known Issues

- No code or benchmark logic changed in this round.
- `review_gpt/round_18_skill_and_figure_redesign_plan.md` remains unrelated and
  untracked.

## Next Steps

- Use these local repositories first for future reference inspection.
- Additional local repositories are not required immediately. They may become
  useful later for independent BCH algebra checks or broader FEC benchmark
  methodology comparison.
