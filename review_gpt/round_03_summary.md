# Round 03 Summary: Public Sanitization and Packed Batch Correctness

## Modified Files

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `scripts/plot_results.py`
- `linear_kernel/packed_batch.py`
- `tests/test_correctness.py`
- `review_gpt/README.md`
- `review_gpt/latest.md`
- `review_gpt/round_03_summary.md`
- sanitized older `review_gpt` notes

## Implementation

- Rewrote public README as a generic GF(2) kernel correctness repo overview.
- Rewrote AGENTS.md as public development rules and fixed the per-round workflow.
- Sanitized review handoff notes to keep them code-focused.
- Added `paper/` and `references/` to `.gitignore`.
- Added `codes/` to `.gitignore` and removed unused code placeholders from public tracking.
- Removed `paper/` and `references/` from git tracking without deleting local files.
- Removed application-specific public package metadata and plotting placeholder wording.
- Implemented `PackedBatchGF2Kernel.apply_many` as correctness-first NumPy `(X @ A) mod 2`.
- Added PackedBatch correctness and invalid-width tests.

## Test Result

```text
49 passed
```

## Known Issues

- `HybridPlanner` is not implemented.
- No formal benchmark results are present.

## Next Step

Push this round to the configured remote.
