# BCH Reference Notes

## Why Triangulate

No single external implementation should be treated as the only correct answer.
Different BCH libraries may use different primitive polynomials, bit order,
position order, shortening conventions, or parity placement. This repository
therefore treats external implementations as behavior references and records
matches or mismatches instead of silently replacing the local matrix.

External source code must not be copied into this repository. External
repositories or packages may be inspected or invoked locally as optional
oracles, with source name, available version or commit, license when known,
parameters, and comparison result recorded.

## Reference Roles

- OFEC_CNN can provide a local implementation-specific behavior reference when
  a user configures its path.
- Linux BCH code can provide an independent systems implementation reference if
  a public-safe adapter is configured.
- python-bchlib can provide an installed package reference if a compatible
  bit-level adapter is available.
- AFF3CT can provide a communication-systems reference if a local build and
  adapter are configured.
- The Python `galois` package can provide a message one-hot encoding reference
  for BCH parameters when installed.

The machine-readable registry is written to
`results/raw/reference_registry.csv`. It records role, suggested source,
license status, adapter status, trust level for BCH math, trust level for oFEC
structure, and notes. This registry is not a ranking of correctness; it is a
record of how each source may be used and what risks remain.

## Reference-Vs-Reference Cross-Check

The reference checker now writes `results/raw/bch_reference_pairwise_check.csv`.
This compares available references against each other under the same convention
transforms used for local-matrix comparison. Unavailable references are recorded
in the registry and local-vs-reference report, but are skipped for pairwise
matrix comparison.

In the current local run, OFEC_CNN and `galois` were both available and matched
each other exactly under the identity transform. That means those two adapters
currently agree with each other for the generated BCH(255,239) syndrome
contribution matrix. This does not make either source a gold standard.

`python-bchlib` was importable and its public API was surveyed. A
`BCH(t=2, m=8)` object reports `n=255`, `ecc_bits=16`, and `ecc_bytes=2`, but
the API is byte-oriented. The exact 239-bit message packing, pad-bit handling,
and bit order have not been validated, so this repository does not yet enable a
python-bchlib behavior adapter.

## Encoding Parity Matrix vs Syndrome Contribution Matrix

For a systematic encoder, the parity part can be written as:

```text
p = u P
```

where `u` is the message vector and `P` has shape `(k, r)`. One-hot encoding
each message bit gives one row of `P`.

For syndrome computation on a full received codeword:

```text
s = y H^T
```

where `y` has length `n` and `H^T` has shape `(n, r)`. This matrix describes
the syndrome contribution of every full codeword position.

For a systematic code, if only the encoding parity matrix `P` is available, a
common candidate syndrome contribution matrix is:

```text
A_syndrome = [P ; I]
```

The bottom identity block corresponds to the parity positions. Exact comparison
still depends on bit order, position order, output packing, and whether an
eBCH-wide parity bit is included.

## One-Hot Probing

One-hot probing means turning on exactly one input position and observing the
reference output. For an encoder, this probes one message bit and records the
parity contribution. For a syndrome calculator, this probes one full codeword
position and records its syndrome contribution directly.

## Current Status

The local `make_bch255_t2_syndrome_matrix()` remains a deterministic
reimplemented placeholder. The reference-check tool writes
`results/raw/bch_reference_check.csv` with availability, transform, shape,
match rate, and exact-match fields.

In the current local run, the configured OFEC_CNN path and the installed
`galois` package were both available. They produced the same comparison pattern
against the current local matrix: no exact match under the tested common
convention transforms. The best observed transform was
`reverse_codeword_positions`, with a match rate of about `0.508`.

`python-bchlib` was importable in this environment, but this repository does
not yet include a public-safe bit-level adapter for BCH(255,239). AFF3CT and
Linux BCH references were not configured.

The current workflow does not assume OFEC_CNN is the gold standard. If no exact
match is found across available references and common convention transforms,
the current matrix remains a placeholder until a public-safe verification path
is established.
