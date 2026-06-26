# Latest Review Summary

Current round: Round 8.1 cache-aware artifact fix + final export data-quality
guard.

## Goal

Fix the Round 08 final artifact chain after review flagged that the cache-aware
evidence files could be empty while still being cited by final figures and
tables.

This round is an artifact/data-quality fix. It does not add a new code profile,
does not run BER, does not implement a full decoder, and does not run a broad
full sweep.

## Skills Used

- `results-analysis`: audited cache-aware CSV row counts, correctness fields,
  required block-width coverage, and final table source validity.
- `paper-figures-advise`: kept figure/table claims aligned with the available
  evidence and avoided empty diagnostic plots.
- `plot-from-data`: used for final figure data-quality expectations.
- `research-experiment-driver`: kept the fix scoped to final artifact
  reproducibility rather than expanding the experiment plan.
- `superpowers:test-driven-development`: added failing tests for empty
  cache-aware export and synthetic candidate-profile selection before fixing.
- `superpowers:verification-before-completion`: used for final verification.

No subagent was used in this round; the work was tightly coupled across one
export script, tests, and review notes.

## What Was Fixed

1. Cache-aware artifact audit:
   - `results/raw/cache_aware.csv`: 9216 rows, non-empty.
   - `results/summary/cache_aware_summary.csv`: 9216 rows, non-empty.
   - Both include `bch_255_239_r16` and `ebch_256_239_r17`.
   - Both include PackedBlockLUT packed-output rows for block widths
     `4,6,8,10,12,14,16,18,20` at `batch_size=4096`, `density=0.05`.
   - Correctness fields are all true.
   - No targeted rerun was needed because the current checked-out artifacts
     are already non-empty and satisfy the final figure requirements.

2. Final exporter data-quality guard:
   - `scripts/export_final_paper_figures.py` now raises `ValueError` when a
     critical CSV or plotted-row subset is empty.
   - Guarded inputs include cache-aware raw/summary rows, long-stream rows,
     cache-aware planner paper rows, candidate full rows, event-update rows,
     BCH syndrome rows, component-loop rows, and component exactness rows.
   - This prevents silent "successful" empty figures.

3. Candidate representative row:
   - `final_representative_table.csv` now prioritizes `bch_255_239_r16`, then
     `ebch_256_239_r17`, before synthetic fallback.
   - The current Candidate testing row uses `bch_255_239_r16`.

4. Regenerated final artifacts:
   - `results/summary/final_claim_audit.csv`
   - `results/summary/final_exactness_table.csv`
   - `results/summary/final_representative_table.csv`
   - `results/paper_figures_final/*.pdf`
   - `results/raw/artifact_provenance.json`

## Modified Files

- `scripts/export_final_paper_figures.py`
- `tests/test_final_paper_export.py`
- `tests/test_result_summary.py`
- `results/summary/final_representative_table.csv`
- `results/raw/artifact_provenance.json`
- `results/paper_figures_final/*.pdf`
- `review_gpt/latest.md`
- `review_gpt/experiment_round_08_summary.md`
- `review_gpt/experiment_round_08_1_cache_aware_artifact_fix.md`

## Commands Run

```bash
python -m pytest tests/test_final_paper_export.py tests/test_result_summary.py -q
python scripts/summarize_results.py
python scripts/export_final_paper_figures.py
python -m pytest -q
```

Results:

- Targeted tests: `12 passed, 1 warning`
- `scripts/summarize_results.py`: completed
- `scripts/export_final_paper_figures.py`: completed
- Full test suite: `298 passed, 1 skipped, 27 warnings`

## Push / Remote Artifact Status

The Round 8.1 commit has been pushed and remote `origin/main` was confirmed at:

```text
5ced7b8f74d333b0710bdf2ce8d8ee9527e6f706
```

Remote GitHub artifact verification:

| File | Local rows | GitHub blob SHA match | GitHub size |
|---|---:|---|---:|
| `results/raw/cache_aware.csv` | 9216 | yes | 2199418 bytes |
| `results/summary/cache_aware_summary.csv` | 9216 | yes | 1650238 bytes |

The GitHub Contents API blob SHA matched the local `HEAD` blob SHA for both
files, so the files on GitHub are the same non-empty 9216-row CSVs checked
locally.

## Claim Boundaries

- `fig_cache_memory_tradeoff` now has non-empty cache-aware block-width data
  behind Panel A/B.
- Long-stream panels still use the corrected `stream_input_bits` /
  `stream_input_bytes` schema.
- L2 remains mixed and is not a stable strong claim.
- L3 remains condition-specific eBCH-like long-stream evidence.
- Optical trace workloads remain trace-level kernel-call evidence, not a full
  decoder or BER result.
- No `paper/`, `references/`, `external_refs/`, `AGENTS.local.md`, or local
  absolute paths should be committed.
