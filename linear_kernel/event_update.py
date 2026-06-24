"""Event-driven syndrome update backend skeleton."""

from __future__ import annotations

import numpy as np

from .matrix_utils import require_gf2_matrix


class EventUpdateKernel:
    """Backend for updating f(x) after a small number of bit flips."""

    def __init__(self, matrix: np.ndarray) -> None:
        self.matrix = require_gf2_matrix(matrix)

    def update(self, current_value: np.ndarray, flipped_positions: np.ndarray) -> np.ndarray:
        """Update an existing output after bit flip events."""
        raise NotImplementedError("EventUpdateKernel.update will be implemented later")
