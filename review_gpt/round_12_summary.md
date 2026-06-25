# Round 12 Summary - Reference Registry and BCH Cross-Check

## Modified Files

- `AGENTS.md`
- `docs/bch_reference_notes.md`
- `tools/verify_bch_references.py`
- `tests/test_bch_reference_tools.py`
- `results/raw/bch_reference_check.csv`
- `results/raw/reference_registry.csv`
- `results/raw/bch_reference_pairwise_check.csv`
- refreshed `results/raw/*.csv`
- refreshed `results/figures/*.png`
- `review_gpt/latest.md`
- `review_gpt/round_12_summary.md`

## Implementation

- Added a Reference Registry section to `AGENTS.md`.
- Added registry metadata rows in the reference-check tool.
- Added `reference_registry.csv` generation.
- Added reference-vs-reference pairwise comparison and
  `bch_reference_pairwise_check.csv` generation.
- Added python-bchlib API survey behavior without enabling an unverified
  adapter.
- Added tests for registry output, pairwise exact-match comparison, and graceful
  CLI generation.

## Reference Results

Available:

- `ofec`
- `galois`

Unavailable or not adapted:

- `python-bchlib`
- `aff3ct`
- `linux-kernel`

`python-bchlib` imports and `BCH(t=2, m=8)` reports `n=255`, `ecc_bits=16`,
`ecc_bytes=2`, and `prim_poly=285`, but the byte-oriented API needs bit-packing
validation before use as an adapter.

Pairwise comparison:

- `ofec` vs `galois`: exact identity match.

Current local matrix:

- no exact match against available references;
- best transform remains `reverse_codeword_positions` with match rate
  `0.5078431372549019`;
- current matrix remains a placeholder.

OFEC_CNN is not treated as a gold standard. No external source code was copied.

## Verification

```text
python -m pytest -q
171 passed
```

```text
python scripts/run_all_benchmarks.py
```

Completed and refreshed benchmark outputs.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Completed with OFEC path supplied through a temporary local environment
variable.

## Known Issues

- Current BCH-like matrix is still a deterministic placeholder.
- No verified replacement matrix was added.
- No full BCH/eBCH decoder, OFEC decoder, HybridPlanner, BER simulation, paper
  conclusion, or speedup claim was added.

## Next Step

Add a public-safe systematic BCH parity-contribution generator matching the
OFEC/galois pairwise reference result.
