# Latest Review Summary

Current round: Round 13 - Pairwise Report Fix and Trust Check

## Modified Files

- `tools/verify_bch_references.py`
- `tests/test_bch_reference_tools.py`
- `results/raw/bch_reference_check.csv`
- `results/raw/reference_registry.csv`
- `results/raw/bch_reference_pairwise_check.csv`
- `results/raw/bch_reference_summary.csv`
- refreshed benchmark CSV/PNG outputs
- `review_gpt/latest.md`
- `review_gpt/round_13_summary.md`

## Issue Investigated

The previous review note said `ofec` vs `galois` had an exact identity match,
but the tracked `results/raw/bch_reference_pairwise_check.csv` contained only a
`not_enough_available_references` row. That was an inconsistent artifact state:
the local-vs-reference CSV and pairwise CSV were not from the same effective
reference run.

## Tool Fix

- Added `results/raw/bch_reference_summary.csv`.
- Added end-of-run console summary:
  - enabled references;
  - available reference names;
  - unavailable reference names;
  - pairwise row count.
- Added `ReferenceSummaryRow` and `build_reference_summary()`.
- Strengthened tests for:
  - two synthetic available references producing pairwise rows;
  - identical pairwise matrices producing `exact_match=True`;
  - one available reference producing a `not_enough_available_references` row
    with a clear reason;
  - summary row consistency with pairwise rows.

## Same-Run Reference Result

The committed reference CSV files were regenerated in one run with the OFEC path
provided through a temporary local environment variable. The concrete local path
is not tracked.

Run summary:

```text
enabled references: ofec,galois,python-bchlib,aff3ct,linux-kernel
available references: ofec,galois
unavailable references: python-bchlib,aff3ct,linux-kernel
pairwise row count: 5
```

`bch_reference_check.csv` and `bch_reference_pairwise_check.csv` are from this
same run.

Pairwise CSV status:

- It contains `ofec` vs `galois`.
- `ofec` vs `galois` identity transform has `exact_match=True`.
- `num_equal_entries=4080`, `num_total_entries=4080`, `match_rate=1.0`.

Summary CSV status:

```text
available_references = ofec;galois
unavailable_references = python-bchlib;aff3ct;linux-kernel
num_pairwise_rows = 5
any_pairwise_exact_match = True
best_pairwise_match = ofec|galois|identity|1.000000
current_matrix_status = placeholder
```

## Matrix Status

Current `make_bch255_t2_syndrome_matrix()` remains a deterministic placeholder.
The pairwise exact match between OFEC and `galois` does not upgrade the current
placeholder matrix to verified, because local-vs-reference comparison still does
not exactly match the placeholder matrix.

## Verification

```text
python -m pytest -q
```

Passed: `173 passed`.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Passed with OFEC path supplied via temporary environment variable and generated
all four reference CSV files.

```text
python scripts/run_all_benchmarks.py
```

Passed and refreshed benchmark CSV/PNG outputs.

## Guardrails

- OFEC_CNN is not treated as a gold standard.
- No external code was copied.
- No new backend, HybridPlanner, full BCH/eBCH decoder, OFEC decoder, paper
  conclusion, or speedup claim was added.

## Next Step

Use the now-consistent OFEC/galois pairwise reference result to add a separate,
clearly named verified-candidate matrix generator in a future round, while
keeping the current placeholder unchanged until that generator has its own
correctness tests.
