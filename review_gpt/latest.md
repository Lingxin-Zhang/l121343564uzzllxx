# Latest Review Summary

Current round: Round 12 - Reference Registry and BCH Cross-Check

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

- Added a full `Reference Registry` section to `AGENTS.md`.
- Added a machine-readable reference metadata registry in
  `tools/verify_bch_references.py`.
- The tool now writes:
  - `results/raw/bch_reference_check.csv`;
  - `results/raw/reference_registry.csv`;
  - `results/raw/bch_reference_pairwise_check.csv`.
- Added reference-vs-reference comparison for available references.
- Added tests for registry rows, pairwise exact-match behavior, and CLI
  generation of all three reports.
- Updated `docs/bch_reference_notes.md` with registry, pairwise, and
  python-bchlib API survey notes.

## Reference Registry

`AGENTS.md` now records the reference registry. The generated
`results/raw/reference_registry.csv` contains 10 entries:

- `linux-kernel-bch`
- `python-bchlib`
- `galois`
- `ofec-cnn-local`
- `aff3ct`
- `ofec-huawei`
- `ofec-decoder-vhdl`
- `ofec-sim`
- `automa-ofec`
- `gnuradio-volk`

No external repository is treated as a gold standard.

## Reference Availability

Available in this run:

- `ofec`: loaded through a temporary local environment variable; not copied.
- `galois`: installed Python package, version `0.4.10`, metadata reports MIT.

Unavailable or not adapted:

- `python-bchlib`: importable and API-surveyed, but no trusted adapter enabled.
- `aff3ct`: path not configured.
- `linux-kernel`: path not configured.

## python-bchlib Survey

`python-bchlib` imports successfully. A `BCH(t=2, m=8)` object reports:

```text
n = 255
ecc_bits = 16
ecc_bytes = 2
prim_poly = 285
```

The public API is byte-oriented, so exact 239-bit message packing, pad-bit
handling, and bit order are not yet validated. This round does not enable a
python-bchlib behavior adapter.

## Cross-Check Result

Current local matrix vs references:

- `ofec` and `galois` both have best local-matrix transform
  `reverse_codeword_positions`.
- Best match rate is `0.5078431372549019`.
- No exact match was found against the current placeholder matrix.

Reference-vs-reference:

- `ofec` vs `galois` has an exact identity match.
- `results/raw/bch_reference_pairwise_check.csv` was generated.

This strengthens evidence that OFEC and `galois` currently agree with each
other, while the current `make_bch255_t2_syndrome_matrix()` remains a
placeholder.

## Verification

```text
python -m pytest -q
171 passed
```

```text
python scripts/run_all_benchmarks.py
```

Completed and refreshed benchmark CSV/PNG outputs.

```text
python tools/verify_bch_references.py --output results/raw/bch_reference_check.csv
```

Completed with OFEC path supplied through a temporary local environment
variable. The concrete local path is not written into tracked files.

## Known Issues

- Current `make_bch255_t2_syndrome_matrix()` remains a deterministic placeholder.
- No verified replacement matrix was added.
- No external implementation code was copied.
- No full BCH/eBCH decoder, OFEC decoder, HybridPlanner, BER simulation, paper
  conclusion, or speedup claim was added.

## Next Step

Add a public-safe function that builds the systematic BCH parity-contribution
matrix matching both OFEC and `galois`, then compare it against the current
placeholder before deciding whether to switch benchmark input matrices.
