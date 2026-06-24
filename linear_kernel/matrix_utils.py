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
