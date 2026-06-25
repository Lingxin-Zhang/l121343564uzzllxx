"""Deterministic candidate error-pattern generators.

These helpers generate GF(2) error masks for kernel benchmarks only. They do
not implement Chase-Pyndiah, ORBGRAND, DEPT, or any complete decoder.
"""

from __future__ import annotations

import itertools
from collections.abc import Sequence

import numpy as np


def make_chase_ii_patterns(
    *,
    n: int,
    p_chase: int,
    positions: Sequence[int] | None = None,
) -> np.ndarray:
    """Enumerate all ``2**p_chase`` masks on selected unreliable positions."""

    n = _require_positive_int(n, "n")
    p_chase = _require_positive_int(p_chase, "p_chase")
    if p_chase > n:
        raise ValueError("p_chase cannot exceed n")
    selected = np.arange(p_chase, dtype=np.int64) if positions is None else np.asarray(positions)
    _require_positions(selected, n, p_chase)

    patterns = np.zeros((1 << p_chase, n), dtype=np.uint8)
    for mask in range(1 << p_chase):
        for bit_index, position in enumerate(selected):
            if (mask >> bit_index) & 1:
                patterns[mask, int(position)] = 1
    return patterns


def make_fixed_weight_patterns(
    *,
    n: int,
    candidate_weight: int,
    candidate_count: int,
    seed: int,
) -> np.ndarray:
    """Generate deterministic fixed-Hamming-weight sparse masks."""

    n = _require_positive_int(n, "n")
    candidate_count = _require_positive_int(candidate_count, "candidate_count")
    candidate_weight = int(candidate_weight)
    if candidate_weight < 0:
        raise ValueError("candidate_weight must be non-negative")
    if candidate_weight > n:
        raise ValueError("candidate_weight cannot exceed n")
    patterns = np.zeros((candidate_count, n), dtype=np.uint8)
    if candidate_weight == 0:
        return patterns

    rng = np.random.default_rng(seed)
    for row in range(candidate_count):
        positions = rng.choice(n, size=candidate_weight, replace=False)
        patterns[row, positions] = 1
    return patterns


def iter_low_order_positions(n: int, max_weight: int) -> list[tuple[int, ...]]:
    """Return deterministic low-order combinations up to ``max_weight``."""

    n = _require_positive_int(n, "n")
    max_weight = int(max_weight)
    if max_weight < 0:
        raise ValueError("max_weight must be non-negative")
    out: list[tuple[int, ...]] = [()]
    for weight in range(1, max_weight + 1):
        out.extend(itertools.combinations(range(n), weight))
    return out


def _require_positive_int(value: int, name: str) -> int:
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _require_positions(positions: np.ndarray, n: int, p_chase: int) -> None:
    if positions.ndim != 1:
        raise ValueError("positions must be 1-D")
    if positions.shape[0] != p_chase:
        raise ValueError("positions length must equal p_chase")
    if not np.issubdtype(positions.dtype, np.integer):
        raise ValueError("positions must contain integers")
    if np.unique(positions).shape[0] != positions.shape[0]:
        raise ValueError("positions must be unique")
    if np.any((positions < 0) | (positions >= n)):
        raise ValueError(f"positions must be in [0, {n})")
