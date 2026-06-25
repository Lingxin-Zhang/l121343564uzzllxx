"""Optional code-parameter helpers.

This package is intentionally generic in the public repository. Add concrete
helpers here only when they are suitable for public review.
"""

from .bch_like import (
    BCH255_T2_SYNDROME_SPEC,
    BCHLikeSyndromeSpec,
    CURRENT_MATRIX_NOTE,
    make_bch_like_reference_matrix,
    make_bch255_t2_syndrome_matrix,
    make_bch255_t2_syndrome_matrix_galois_systematic,
)
from .matrix_sources import MATRIX_SOURCE_NAMES, get_matrix_source

__all__ = [
    "BCH255_T2_SYNDROME_SPEC",
    "BCHLikeSyndromeSpec",
    "CURRENT_MATRIX_NOTE",
    "make_bch_like_reference_matrix",
    "make_bch255_t2_syndrome_matrix",
    "make_bch255_t2_syndrome_matrix_galois_systematic",
    "MATRIX_SOURCE_NAMES",
    "get_matrix_source",
]
