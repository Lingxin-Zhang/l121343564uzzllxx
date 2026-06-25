"""Named code-size profiles for benchmark sweeps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .matrix_sources import get_matrix_source


@dataclass(frozen=True)
class CodeProfile:
    """Public benchmark profile for a fixed GF(2) linear kernel."""

    profile_name: str
    n: int
    r: int
    matrix_source: str
    matrix_kind: str
    is_synthetic: bool
    notes: str


_PROFILES = (
    CodeProfile(
        profile_name="bch_255_239_r16",
        n=255,
        r=16,
        matrix_source="galois_systematic_candidate",
        matrix_kind="bch_candidate",
        is_synthetic=False,
        notes="BCH(255,239)-candidate matrix from the galois-systematic source.",
    ),
    CodeProfile(
        profile_name="ebch_256_239_r17",
        n=256,
        r=17,
        matrix_source="galois_systematic_candidate_extended",
        matrix_kind="ebch_like_candidate",
        is_synthetic=False,
        notes="eBCH-like candidate formed by extending the BCH candidate with one parity-style bit.",
    ),
    CodeProfile(
        profile_name="synthetic_bch_like_127_r14",
        n=127,
        r=14,
        matrix_source="synthetic_seed_20260713",
        matrix_kind="synthetic_bch_like",
        is_synthetic=True,
        notes="Deterministic synthetic workload; not claimed to be a real BCH matrix.",
    ),
    CodeProfile(
        profile_name="synthetic_511_r32",
        n=511,
        r=32,
        matrix_source="synthetic_seed_20260714",
        matrix_kind="synthetic_large",
        is_synthetic=True,
        notes="Deterministic larger-kernel workload; not claimed to be a real BCH matrix.",
    ),
)


def list_code_profiles() -> list[CodeProfile]:
    """Return supported profiles in stable reporting order."""

    return list(_PROFILES)


def get_code_profile(name: str) -> CodeProfile:
    """Return one named code profile."""

    normalized = name.strip()
    for profile in _PROFILES:
        if profile.profile_name == normalized:
            return profile
    valid = ", ".join(profile.profile_name for profile in _PROFILES)
    raise ValueError(f"unknown code profile {name!r}; expected one of: {valid}")


def get_profile_matrix(name: str) -> np.ndarray:
    """Return the GF(2) matrix associated with a code profile."""

    profile = get_code_profile(name)
    if profile.profile_name == "bch_255_239_r16":
        matrix = get_matrix_source("galois_systematic_candidate")
    elif profile.profile_name == "ebch_256_239_r17":
        matrix = _make_ebch_like_matrix()
    elif profile.profile_name == "synthetic_bch_like_127_r14":
        matrix = _make_synthetic_matrix(profile.n, profile.r, seed=20260713)
    elif profile.profile_name == "synthetic_511_r32":
        matrix = _make_synthetic_matrix(profile.n, profile.r, seed=20260714)
    else:
        raise AssertionError(f"unhandled profile: {profile.profile_name}")
    return _require_profile_matrix(matrix, profile)


def _make_ebch_like_matrix() -> np.ndarray:
    base = get_matrix_source("galois_systematic_candidate")
    matrix = np.zeros((256, 17), dtype=np.uint8)
    matrix[:255, :16] = base
    matrix[:255, 16] = 1
    matrix[255, 16] = 1
    return matrix


def _make_synthetic_matrix(n: int, r: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    matrix = rng.integers(0, 2, size=(n, r), dtype=np.uint8)
    for bit in range(min(n, r)):
        matrix[bit, bit] = 1
    return matrix


def _require_profile_matrix(matrix: np.ndarray, profile: CodeProfile) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.uint8) & 1
    if matrix.shape != (profile.n, profile.r):
        raise ValueError(
            f"profile {profile.profile_name!r} returned shape {matrix.shape}, "
            f"expected {(profile.n, profile.r)}"
        )
    return matrix
