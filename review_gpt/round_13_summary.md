# Round 13 Summary - Pairwise Report Fix and Trust Check

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

## Fix

- Reproduced the inconsistent artifact state: local-vs-reference CSV showed
  `ofec` and `galois` available, while pairwise CSV only had
  `not_enough_available_references`.
- Added summary CSV output to make enabled/available/unavailable reference state
  explicit.
- Added end-of-run console summary.
- Regenerated reference CSV files in one run using a temporary local OFEC path
  environment variable.

## Current Reference Result

- `ofec` available: yes.
- `galois` available: yes.
- `bch_reference_check.csv` and `bch_reference_pairwise_check.csv` are from the
  same run.
- `bch_reference_pairwise_check.csv` contains `ofec` vs `galois`.
- `ofec` vs `galois` identity comparison has `exact_match=True`.
- `bch_reference_summary.csv` records:
  - `available_references = ofec;galois`
  - `num_pairwise_rows = 5`
  - `best_pairwise_match = ofec|galois|identity|1.000000`
  - `current_matrix_status = placeholder`

## Matrix Status

Current `make_bch255_t2_syndrome_matrix()` remains a placeholder. The current
placeholder was not upgraded to verified.

## Verification

```text
python -m pytest -q
173 passed
```

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Completed with the OFEC path supplied through a temporary environment variable.

```text
python scripts/run_all_benchmarks.py
```

Completed and refreshed benchmark outputs.

## Guardrails

- OFEC_CNN is not a gold standard.
- No external source code was copied.
- No new backend, HybridPlanner, full decoder, paper conclusion, or speedup
  claim was added.
