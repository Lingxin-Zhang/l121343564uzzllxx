"""Extended-BCH-like component-code parameter placeholder."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EBCHLikeCode:
    """Container for eBCH-like component-code parameters."""

    n: int
    k: int
    t: int
    has_overall_parity: bool = True
