"""Utilities for unpacked GF(2) arrays."""

from __future__ import annotations

import numpy as np


def as_gf2_array(array: np.ndarray) -> np.ndarray:
    """Return an unsigned 8-bit view/copy with values reduced modulo 2."""
    return np.asarray(array, dtype=np.uint8) & 1


def require_gf2_matrix(matrix: np.ndarray) -> np.ndarray:
    """Validate and normalize a 2-D GF(2) matrix."""
    matrix = as_gf2_array(matrix)
    if matrix.ndim != 2:
        raise ValueError("GF(2) kernel matrix must be 2-D")
    return matrix


def require_gf2_vector(vector: np.ndarray, expected_length: int) -> np.ndarray:
    """Validate and normalize a 1-D GF(2) vector of length ``expected_length``."""
    vector = as_gf2_array(vector)
    if vector.ndim != 1:
        raise ValueError("GF(2) input vector must be 1-D")
    if vector.shape[0] != expected_length:
        raise ValueError(
            f"GF(2) input vector length {vector.shape[0]} does not match matrix n={expected_length}"
        )
    return vector


def require_gf2_batch(batch: np.ndarray, expected_length: int) -> np.ndarray:
    """Validate and normalize a 2-D GF(2) batch with row length ``expected_length``."""
    batch = as_gf2_array(batch)
    if batch.ndim != 2:
        raise ValueError("GF(2) input batch must be 2-D")
    if batch.shape[1] != expected_length:
        raise ValueError(
            f"GF(2) input batch width {batch.shape[1]} does not match matrix n={expected_length}"
        )
    return batch


def _require_pack_width(width: int) -> int:
    width = int(width)
    if width < 1 or width > 16:
        raise ValueError("GF(2) uint16 packing width must be in [1, 16], at most 16")
    return width


def pack_bits_to_uint16(bits: np.ndarray) -> np.uint16:
    """Pack a 1-D GF(2) bit vector into one ``np.uint16``.

    Bit order is little-endian within the integer: ``bits[0]`` maps to uint16
    bit 0, ``bits[1]`` maps to bit 1, and so on up to ``bits[15]``.
    """
    bits = as_gf2_array(bits)
    if bits.ndim != 1:
        raise ValueError("GF(2) bits to pack must be 1-D")
    width = _require_pack_width(bits.shape[0])
    weights = (np.uint16(1) << np.arange(width, dtype=np.uint16)).astype(np.uint16)
    return np.uint16(np.sum(bits.astype(np.uint16) * weights, dtype=np.uint16))


def unpack_uint16_to_bits(value: np.uint16 | int, width: int) -> np.ndarray:
    """Unpack one ``np.uint16`` into a 1-D GF(2) bit vector.

    Bit order is little-endian within the integer: uint16 bit 0 becomes
    ``bits[0]``, bit 1 becomes ``bits[1]``, and so on up to ``width - 1``.
    """
    width = _require_pack_width(width)
    value = np.uint16(value)
    shifts = np.arange(width, dtype=np.uint16)
    return ((value >> shifts) & np.uint16(1)).astype(np.uint8)


def pack_batch_bits_to_uint16(batch_bits: np.ndarray) -> np.ndarray:
    """Pack a 2-D GF(2) bit matrix into one ``np.uint16`` per row.

    For each row, column 0 maps to uint16 bit 0, column 1 maps to bit 1, and so
    on up to column 15.
    """
    batch_bits = as_gf2_array(batch_bits)
    if batch_bits.ndim != 2:
        raise ValueError("GF(2) batch bits to pack must be 2-D")
    width = _require_pack_width(batch_bits.shape[1])
    weights = (np.uint16(1) << np.arange(width, dtype=np.uint16)).astype(np.uint16)
    return (batch_bits.astype(np.uint16) @ weights).astype(np.uint16)
