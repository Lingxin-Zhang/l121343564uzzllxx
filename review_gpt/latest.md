# Latest Review Summary

Current round: Round 14 - Verified-Candidate BCH Matrix and Dependency Check

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
- The existing `make_bch255_t2_syndrome_matrix()` placeholder was retained.
- The new candidate uses `galois.BCH(255, 239)` one-hot message encoding,
  extracts the systematic parity matrix `P`, and returns `[P ; I_16]`.
- The benchmark default matrix was not changed.
- No external implementation code was copied.

## Reference Results

The reference reports were regenerated in one run with the OFEC path supplied
through a temporary local environment variable. The concrete local path is not
tracked.

Run summary:

```text
enabled references: ofec,galois,python-bchlib,aff3ct,linux-kernel
available references: ofec,galois
unavailable references: python-bchlib,aff3ct,linux-kernel
pairwise row count: 5
candidate row count: 26
dependency row count: 6
```

`bch_reference_check.csv`, `bch_reference_pairwise_check.csv`,
`bch_reference_summary.csv`, `bch_matrix_candidate_check.csv`, and
`ofec_dependency_check.csv` are from this same run.

Candidate status:

- `galois_systematic_candidate` exactly matches `galois` under identity.
- `galois_systematic_candidate` exactly matches `ofec` under identity.
- `placeholder` remains non-exact against the available references.
- `make_bch255_t2_syndrome_matrix()` is still a placeholder.

Pairwise status:

- `bch_reference_pairwise_check.csv` contains `ofec` vs `galois`.
- `ofec` vs `galois` identity transform has `exact_match=True`.
- `best_pairwise_match = ofec|galois|identity|1.000000`.

Dependency status:

- `ofec_dependency_check.csv` was generated.
- The inspected OFEC source includes direct `galois` usage in `_ebch_lut.py`.
- Therefore OFEC_CNN and `galois` are convention-aligned in this run, but they
  are not independent references.

## Verification

```text
python -m pytest -q
```

Passed: `179 passed, 1 skipped`.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Passed with OFEC path supplied via temporary environment variable.

```text
python scripts/run_all_benchmarks.py
```

Passed and refreshed benchmark CSV/PNG outputs.

## Known Issues

- `python-bchlib` is still not enabled as a trusted bit-level adapter.
- AFF3CT and Linux BCH paths are not configured.
- OFEC_CNN and `galois` should not be counted as independent references when
  OFEC source directly builds tables from `galois`.

## Next Step

Add an independent public-safe BCH behavior adapter or dependency-free
cross-check before replacing any benchmark default workload.
