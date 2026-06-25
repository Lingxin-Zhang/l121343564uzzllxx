"""Deterministic BCH-like component syndrome matrix helpers.

This module intentionally contains a clean, public reimplementation for a
generic component syndrome workload. The matrix is suitable for exercising
GF(2) kernels with a stable ``(255, 16)`` shape, but it is not yet verified
against any external BCH/eBCH reference implementation.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CURRENT_MATRIX_NOTE = (
    "Current BCH-like matrix is a deterministic reimplemented "
    "component-kernel placeholder, not yet verified against OFEC_CNN."
)


@dataclass(frozen=True)
class BCHLikeSyndromeSpec:
    """Public metadata for a deterministic BCH-like syndrome matrix."""

    name: str
    n: int
    r: int
    primitive_polynomial: int
    source_note: str


BCH255_T2_SYNDROME_SPEC = BCHLikeSyndromeSpec(
    name="bch255_t2_syndrome_placeholder",
    n=255,
    r=16,
    primitive_polynomial=0x11D,
    source_note=CURRENT_MATRIX_NOTE,
)


def _gf256_mul(left: int, right: int, primitive_polynomial: int) -> int:
    """Multiply two GF(2^8) values with a polynomial-basis reduction."""
    result = 0
    a = int(left)
    b = int(right)
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & 0x100:
            a ^= primitive_polynomial
    return result & 0xFF


def _alpha_power(power: int, primitive_polynomial: int) -> int:
    value = 1
    alpha = 2
    for _ in range(power % 255):
        value = _gf256_mul(value, alpha, primitive_polynomial)
    return value


def _byte_to_little_endian_bits(value: int) -> np.ndarray:
    shifts = np.arange(8, dtype=np.uint8)
    return ((np.uint8(value) >> shifts) & np.uint8(1)).astype(np.uint8)


def make_bch255_t2_syndrome_matrix() -> np.ndarray:
    """Return a deterministic ``(255, 16)`` BCH-like syndrome matrix.

    The two 8-bit halves use polynomial-basis coordinates of ``alpha^j`` and
    ``alpha^(3j)`` for input position ``j``. Bit order inside each byte is
    little-endian: column 0 stores coefficient bit 0 of the first syndrome
    byte, column 8 stores coefficient bit 0 of the second syndrome byte.

    Current BCH-like matrix is a deterministic reimplemented component-kernel
    placeholder, not yet verified against OFEC_CNN.
    """
    spec = BCH255_T2_SYNDROME_SPEC
    matrix = np.zeros((spec.n, spec.r), dtype=np.uint8)
    for position in range(spec.n):
        first = _alpha_power(position, spec.primitive_polynomial)
        third = _alpha_power(3 * position, spec.primitive_polynomial)
        matrix[position, :8] = _byte_to_little_endian_bits(first)
        matrix[position, 8:] = _byte_to_little_endian_bits(third)
    return matrix


def make_bch255_t2_syndrome_matrix_galois_systematic() -> np.ndarray:
    """Return a verified-candidate systematic BCH(255,239) matrix.

    This matrix is built from the Python ``galois`` package by one-hot
    encoding each message position of ``galois.BCH(255, 239)``. If the
    resulting systematic codeword is ``c = [u | p]`` and ``p = u P``, this
    helper returns the syndrome contribution candidate ``A = [P ; I_16]``.

    The result is separate from ``make_bch255_t2_syndrome_matrix()``, which is
    retained as a deterministic public workload placeholder. This candidate is
    suitable for reference checks against available implementations; it is not
    claimed to be an official OIF/oFEC matrix.

    Raises:
        RuntimeError: If the optional ``galois`` dependency is not installed.
    """
    try:
        import galois
    except ImportError as exc:
        raise RuntimeError(
            "galois is required to build the verified-candidate BCH matrix"
        ) from exc

    n = 255
    k = 239
    r = n - k
    bch = galois.BCH(n, k)
    parity_rows = []
    basis = np.zeros(k, dtype=np.int32)
    for position in range(k):
        basis.fill(0)
        basis[position] = 1
        codeword = np.asarray(bch.encode(basis), dtype=np.int32)
        parity_rows.append((codeword[k:] & 1).astype(np.uint8, copy=False))
    parity_matrix = np.stack(parity_rows, axis=0).astype(np.uint8, copy=False)
    matrix = np.concatenate([parity_matrix, np.eye(r, dtype=np.uint8)], axis=0)
    return matrix.astype(np.uint8, copy=False)


def make_bch_like_reference_matrix() -> np.ndarray:
    """Compatibility alias for the public deterministic component matrix."""
    return make_bch255_t2_syndrome_matrix()
