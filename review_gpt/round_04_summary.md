# Round 04 Summary: Restore Codes Directory Tracking

## Modified Files

- `.gitignore`
- `codes/__init__.py`
- `pyproject.toml`
- `review_gpt/latest.md`
- `review_gpt/round_04_summary.md`

## Implementation

- Addressed review feedback that ignoring the whole `codes/` directory would hide future public code from git and code review.
- Removed the broad `codes/` ignore rule.
- Kept only narrow ignore rules for existing local sensitive placeholder files:
  - `codes/bch_like.py`
  - `codes/ebch_like.py`
- Reintroduced a generic `codes/__init__.py` that contains no sensitive application details.
- Restored `codes*` in package discovery.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
49 passed
```

## Known Issues

- `HybridPlanner` is not implemented.
- No formal benchmark results are present.

## Next Step

Commit and push this round.
