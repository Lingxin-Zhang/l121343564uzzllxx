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

## Subagent Collaboration

Use subagents only when the user explicitly asks for subagents, delegation, or
parallel agent work, or when a later project instruction authorizes it for a
specific round. Keep the main agent responsible for integration, final
verification, commits, and pushes.

Good subagent tasks:

1. Independent codebase exploration, such as checking whether a backend API is
   used consistently across tests, benchmarks, and plotting code.
2. Independent result review, such as reading generated CSV files and reporting
   backend ranking or suspicious measurements.
3. Parallel experiment execution, when each agent owns a separate benchmark
   configuration or remote run and writes results to disjoint files.
4. Plot or documentation review, where the agent checks labels, legends,
   tracked artifacts, and public-repository wording.
5. Code review before commit, especially for correctness risks, missing tests,
   benchmark methodology problems, or accidental sensitive-file exposure.

Avoid subagents for:

1. Immediate blocking work on the critical path that the main agent needs before
   taking the next step.
2. Highly coupled edits to the same files, unless ownership is clearly split.
3. Tasks requiring credentials, passwords, or local sensitive paths. Keep those
   in the main thread or untracked local files only.
4. Final claims of success. The main agent must rerun the relevant verification
   commands and inspect the final diff.

When delegating code changes, give each subagent a concrete, self-contained task
and a disjoint file ownership scope. Tell subagents that other work may be
happening in parallel and that they must not revert unrelated changes.

## Skill Usage

Before starting a round, check whether an available skill matches the task. Use
the most relevant skill when it fits the work, especially for:

1. Python implementation and correctness testing.
2. Pytest-driven verification.
3. Benchmark or remote-experiment execution.
4. Markdown documentation and review notes.
5. Git/GitHub commit and push workflows.
6. Subagent coordination when the user explicitly asks for parallel agents.

If a skill's instructions conflict with an explicit user request or this
repository's workflow, follow the user request and repository workflow, and note
the reason briefly in the working notes or final summary when relevant.

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
11. If suitable agent skills are available, such as Python, pytest, benchmark,
    remote-experiment, Markdown, subagent, or Git/GitHub skills, use them when
    they fit the task.
