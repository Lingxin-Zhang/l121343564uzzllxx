"""Workload-aware backend planner skeleton."""

from __future__ import annotations

import numpy as np


class HybridPlanner:
    """Select a bit-exact backend based on workload characteristics."""

    def choose_backend(self, matrix: np.ndarray, workload: dict) -> object:
        """Return the backend instance expected to be best for the workload."""
        raise NotImplementedError("HybridPlanner.choose_backend will be implemented later")
