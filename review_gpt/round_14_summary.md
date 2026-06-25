# Round 14 Summary - Verified-Candidate BCH Matrix and Dependency Check

## Modified Files

- `codes/bch_like.py`
- `codes/__init__.py`
- `tools/verify_bch_references.py`
- `tests/test_bch_reference_tools.py`
- `tests/test_bch_verified_candidate.py`
- `docs/bch_reference_notes.md`
- `README.md`
- `results/raw/bch_reference_check.csv`
- `results/raw/reference_registry.csv`
- `results/raw/bch_reference_pairwise_check.csv`
- `results/raw/bch_reference_summary.csv`
- `results/raw/bch_matrix_candidate_check.csv`
- `results/raw/ofec_dependency_check.csv`
- refreshed benchmark CSV/PNG outputs
- `review_gpt/latest.md`
- `review_gpt/round_14_summary.md`

## Implementation

- Added `make_bch255_t2_syndrome_matrix_galois_systematic()`.
- Kept the existing deterministic placeholder matrix unchanged.
- Added candidate comparison output in
  `results/raw/bch_matrix_candidate_check.csv`.
- Added OFEC source dependency inspection output in
  `results/raw/ofec_dependency_check.csv`.
- Added tests for candidate shape, dtype, bit values, determinism, systematic
  zero syndrome behavior, exact match against the `galois` probe, candidate
  report rows, and dependency inspection.

## Results

- `galois_systematic_candidate` exact match vs `galois`: yes, identity.
- `galois_systematic_candidate` exact match vs OFEC_CNN: yes, identity in the
  local configured run.
- `bch_reference_pairwise_check.csv` includes `ofec` vs `galois`.
- `ofec` vs `galois` exact match: yes, identity.
- OFEC_CNN directly uses `galois` in the inspected source, so the two are
  convention-aligned but not independent references.
- Benchmark default matrix changed: no.
- External code copied: no.

## Verification

```text
python -m pytest -q
```

Passed: `179 passed, 1 skipped`.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Passed with the OFEC path supplied via temporary local environment variable.

```text
python scripts/run_all_benchmarks.py
```

Passed and refreshed benchmark CSV/PNG outputs.

## Known Issues

- The placeholder remains placeholder.
- `python-bchlib`, AFF3CT, and Linux BCH are not yet active trusted behavior
  adapters.
- More independent validation is needed before replacing any default benchmark
  workload.
