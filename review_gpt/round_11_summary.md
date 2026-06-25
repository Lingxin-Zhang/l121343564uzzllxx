# Round 11 Summary - BCH Reference Triangulation

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

- Added an optional BCH reference-check tool.
- Added comparison utilities for exact matrix comparison and common convention
  transforms.
- Added graceful unavailable-reference rows for missing or unsupported sources.
- Added docs explaining encoding parity matrix vs syndrome contribution matrix.
- Updated public reference policy in README and AGENTS.

## Reference Result

OFEC_CNN was not treated as the only standard answer. It was one optional local
reference. No external source code was copied.

Available references in this run:

- `ofec`
- `galois`

Unavailable or not adapted:

- `python-bchlib`
- `aff3ct`
- `linux-kernel`

No exact match was found. The best tested transform for both available
references was `reverse_codeword_positions`, with match rate
`0.5078431372549019`. The current matrix therefore remains a placeholder.

Possible convention differences include primitive polynomial, bit order,
position order, output packing, and eBCH-wide parity handling. This round does
not identify one definitive cause.

## Verification

```text
python -m pytest -q
168 passed
```

```text
python scripts/run_all_benchmarks.py
```

Completed and refreshed benchmark outputs.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Completed with the OFEC path supplied through a temporary local environment
variable, and generated `results/raw/bch_reference_check.csv`.

## Known Issues

- Current BCH-like matrix is still a deterministic placeholder.
- No verified replacement matrix was added.
- Push to GitHub failed from this environment after repeated attempts because
  connecting to `github.com:443` timed out or reset. Local commit exists and is
  one commit ahead of `origin/main`.
- No full BCH/eBCH decoder, OFEC decoder, HybridPlanner, BER simulation, paper
  conclusion, or speedup claim was added.

## Next Step

Implement a public-safe systematic BCH parity-contribution generator and compare
it against OFEC_CNN and `galois`.
