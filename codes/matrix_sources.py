"""Named matrix sources for benchmarks and workload tests."""

from __future__ import annotations

import numpy as np

from .bch_like import (
    make_bch255_t2_syndrome_matrix,
    make_bch255_t2_syndrome_matrix_galois_systematic,
)

N = 255
R = 16
RANDOM_FIXED_SEED = 20260628
MATRIX_SOURCE_NAMES = (
    "placeholder",
    "galois_systematic_candidate",
    "random_fixed",
)


def _require_public_gf2_matrix(matrix: np.ndarray, source_name: str) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.uint8)
    if matrix.shape != (N, R):
        raise ValueError(
            f"matrix source {source_name!r} returned shape {matrix.shape}, expected {(N, R)}"
        )
    if not np.all((matrix == 0) | (matrix == 1)):
        raise ValueError(f"matrix source {source_name!r} must contain only 0/1 values")
    return matrix


def get_matrix_source(name: str) -> np.ndarray:
    """Return a named ``(255, 16)`` GF(2) matrix.

    Supported names are:

    - ``placeholder``: deterministic public BCH-like placeholder.
    - ``galois_systematic_candidate``: verified-candidate matrix built with
      the optional ``galois`` dependency.
    - ``random_fixed``: deterministic random GF(2) matrix used by generic
      micro-benchmarks.
    """
    normalized = name.strip()
    if normalized == "placeholder":
        matrix = make_bch255_t2_syndrome_matrix()
    elif normalized == "galois_systematic_candidate":
        matrix = make_bch255_t2_syndrome_matrix_galois_systematic()
    elif normalized == "random_fixed":
        rng = np.random.default_rng(RANDOM_FIXED_SEED)
        matrix = rng.integers(0, 2, size=(N, R), dtype=np.uint8)
    else:
        valid = ", ".join(MATRIX_SOURCE_NAMES)
        raise ValueError(f"unknown matrix source {name!r}; expected one of: {valid}")
    return _require_public_gf2_matrix(matrix, normalized)
