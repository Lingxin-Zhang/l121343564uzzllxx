"""BCH-like component-code parameter placeholder."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BCHLikeCode:
    """Container for BCH-like component-code parameters."""

    n: int
    k: int
    t: int
