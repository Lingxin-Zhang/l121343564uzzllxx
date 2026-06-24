"""Utilities for GF(2) matrices.

Only lightweight validation helpers should live here until the backend
implementations are added.
"""

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
