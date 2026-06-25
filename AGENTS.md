# AGENTS.md

## Project Scope

This is a public GF(2) kernel benchmark and correctness project. Keep the
repository focused on small, testable backend implementations, correctness
checks, reproducible micro-benchmarks, plotting scripts, and code-focused
development notes.

## Development Rules

- Correctness comes first.
- Do not invent benchmark results, speedup numbers, or conclusions.
- Do not claim performance improvements unless reproducible benchmark data and
  methodology are present.
- Do not commit local sensitive documents, private notes, drafts, or unpublished
  research materials.
- Keep public documentation generic and code-focused.
- Do not reintroduce ignored local `paper/` or `references/` content into git.
- Local reference implementations may be consulted only for parameters or
  calling patterns. Do not copy large code blocks; reimplement needed logic in
  this repository.
- Put concrete local reference paths in untracked `AGENTS.local.md`, not in
  committed files.

## Backend Status

Implemented:

1. `NaiveGF2Kernel`
2. `SparseXorKernel`
3. `BlockLUTKernel`
4. `EventUpdateKernel`
5. `PackedBatchGF2Kernel.apply_many`
6. `PackedBlockLUTKernel`

Not implemented:

1. `HybridPlanner`

## Benchmark Status

Implemented:

1. `benchmarks/bench_block_width.py`
2. `benchmarks/bench_density.py`
3. `benchmarks/bench_batch.py`
4. `benchmarks/bench_stream.py`
5. `scripts/plot_results.py`
6. `scripts/run_all_benchmarks.py`
7. `scripts/run_all_benchmarks.sh`

Generated CSV and PNG figure outputs may be tracked for review. PDF figures are
local artifacts unless explicitly requested.

## Per-Round Workflow

Every modification round must follow this workflow:

1. Confirm the current round goal before making unrelated changes.
2. Run relevant tests after code changes, at least `pytest`.
3. Do not invent benchmark results, speedup numbers, or paper conclusions.
4. Update `review_gpt/latest.md` before ending the round.
5. Create or update the matching `review_gpt/round_xx_summary.md`.
6. Keep `review_gpt` code-focused: modified files, implementation details,
   test results, known issues, and next steps.
7. Do not write unpublished paper stories, venue details, novelty details, or
   sensitive experiment ideas in `review_gpt`.
8. Commit completed changes with `git commit`.
9. Push completed changes to `Lingxin-Zhang/l121343564uzzllxx`.
10. If tests or push cannot be completed, document the reason in
    `review_gpt/latest.md`.
11. If suitable agent skills are available, such as Python, pytest, Markdown, or
    Git/GitHub skills, use them when they fit the task.
