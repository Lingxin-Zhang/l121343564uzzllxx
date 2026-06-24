# AGENTS.md

## Project Scope

This is a public GF(2) kernel benchmark and correctness project. Keep the
repository focused on small, testable backend implementations, correctness
checks, and reproducible development notes.

## Development Rules

- Correctness comes first.
- Do not invent benchmark results, speedup numbers, or conclusions.
- Do not claim performance improvements unless reproducible benchmark data and
  methodology are present.
- Do not commit local sensitive documents, private notes, drafts, or unpublished
  research materials.
- Keep public documentation generic and code-focused.

## Backend Status

Implemented:

1. `NaiveGF2Kernel`
2. `SparseXorKernel`
3. `BlockLUTKernel`
4. `EventUpdateKernel`
5. `PackedBatchGF2Kernel.apply_many`

Not implemented:

1. `HybridPlanner`
2. Formal benchmark runs

## 每轮工作流

每轮修改必须遵守：

1. 开始前先确认本轮目标，不要顺手做无关任务。
2. 修改代码后必须运行相关测试，至少运行 pytest。
3. 不得编造 benchmark 结果、speedup 数字或论文结论。
4. 每轮结束必须更新 `review_gpt/latest.md`。
5. 每轮结束必须新建或更新对应 `round_xx_summary.md`。
6. `review_gpt` 中只写代码层面的信息：修改文件、实现内容、测试结果、已知问题、下一步建议。
7. `review_gpt` 中不要写未公开论文故事、投稿 venue、创新点细节或敏感实验构思。
8. 修改完成后必须 `git commit`。
9. 修改完成后必须 push 到远程仓库 `Lingxin-Zhang/l121343564uzzllxx`。
10. 如果无法完成测试或 push，必须在 `review_gpt/latest.md` 中说明原因。
11. 如果环境中有适合的 agent skill，例如 Python、pytest、Markdown、Git/GitHub 相关 skill，请优先使用。
