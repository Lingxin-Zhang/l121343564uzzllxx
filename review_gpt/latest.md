# Latest Review Summary

Current round: Round 11 - BCH Reference Triangulation

## Modified Files

- `.gitignore`
- `AGENTS.md`
- `README.md`
- `docs/bch_reference_notes.md`
- `tools/__init__.py`
- `tools/verify_bch_references.py`
- `tests/test_bch_reference_tools.py`
- `results/raw/bch_reference_check.csv`
- refreshed `results/raw/*.csv`
- refreshed `results/figures/*.png`
- `review_gpt/latest.md`
- `review_gpt/round_11_summary.md`

## Implementation

- Added `tools/verify_bch_references.py`, an optional/local-friendly reference
  triangulation tool.
- The tool compares the current local `make_bch255_t2_syndrome_matrix()` output
  against available references and writes `results/raw/bch_reference_check.csv`.
- The tool reports unavailable references gracefully instead of crashing.
- Added common convention checks:
  - identity;
  - reverse codeword position order;
  - reverse bit order inside each output byte;
  - reverse output byte order;
  - reverse output bit order;
  - drop an eBCH-wide parity row when a 256-row reference appears.
- Added lightweight tests for CLI help, exact-match comparison, reversed-position
  detection, and graceful unavailable-reference reporting.
- Added `docs/bch_reference_notes.md` explaining:
  - why OFEC_CNN is not treated as the only gold standard;
  - the difference between an encoding parity matrix and a syndrome contribution
    matrix;
  - one-hot probing;
  - current availability and match status.
- Added `external_refs/` to `.gitignore`.
- Updated `AGENTS.md` and `README.md` to clarify external BCH reference policy.

## Reference Availability

OFEC_CNN was used as one optional local reference in this run, not as the only
standard answer. No external source code was copied into this repository.

Available in this environment:

- `ofec`: available through a configured local path; source code was invoked as
  a behavior reference only.
- `galois`: available as installed Python package `0.4.10`, license reported as
  MIT by package metadata.

Unavailable or not adapted:

- `python-bchlib`: importable, but this repository does not yet have a
  public-safe bit-level BCH(255,239) adapter.
- `aff3ct`: path not configured.
- `linux-kernel`: path not configured.

## Reference Result

No exact match was found between the current local matrix and the available
references under the tested transforms.

Best observed transform for both OFEC_CNN and `galois`:

```text
candidate_transform = reverse_codeword_positions
match_rate = 0.5078431372549019
exact_match = False
```

This suggests the current matrix remains a placeholder. Possible convention or
construction differences include primitive polynomial, bit order, position
order, output packing, and eBCH-wide parity handling. The current result is not
strong evidence for any single explanation.

## Verification

```text
python -m pytest -q
168 passed
```

```text
python scripts/run_all_benchmarks.py
```

Completed and refreshed benchmark CSV/PNG outputs.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Completed with the OFEC path supplied through a temporary local environment
variable, and generated the committed reference-check CSV. The concrete local
path is not written into tracked files.

## Known Issues

- Current `make_bch255_t2_syndrome_matrix()` remains a deterministic placeholder.
- No verified replacement matrix was added.
- Push to GitHub failed from this environment after repeated attempts because
  connecting to `github.com:443` timed out or reset. Local commit exists and is
  one commit ahead of `origin/main`.
- No full BCH/eBCH decoder, OFEC decoder, HybridPlanner, BER simulation, paper
  conclusion, or speedup claim was added.

## Next Step

Add a public-safe adapter for the true systematic BCH parity-contribution matrix
and compare it against both OFEC_CNN and `galois` before changing the benchmark
matrix.
