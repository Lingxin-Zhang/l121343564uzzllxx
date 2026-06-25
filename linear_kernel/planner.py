"""Simple workload-aware backend planner."""

from __future__ import annotations

import numpy as np

from .event_update import EventUpdateKernel
from .matrix_utils import require_gf2_batch, require_gf2_matrix, require_gf2_vector
from .naive import NaiveGF2Kernel
from .packed_batch import PackedBatchGF2Kernel
from .packed_block_lut import PackedBlockLUTKernel
from .sparse_xor import SparseXorKernel


class HybridPlanner:
    """Rule-based dispatcher for bit-exact GF(2) backend calls.

    This is a reproducible baseline planner, not an optimal scheduler.
    """

    def __init__(
        self,
        matrix: np.ndarray,
        *,
        block_width: int = 8,
        sparse_threshold: int = 8,
        batch_threshold: int = 64,
    ) -> None:
        self.matrix = require_gf2_matrix(matrix)
        self.n, self.r = self.matrix.shape
        self.block_width = int(block_width)
        self.sparse_threshold = int(sparse_threshold)
        self.batch_threshold = int(batch_threshold)
        if self.sparse_threshold < 0:
            raise ValueError("sparse_threshold must be non-negative")
        if self.batch_threshold < 1:
            raise ValueError("batch_threshold must be positive")

        self.naive = NaiveGF2Kernel(self.matrix)
        self.sparse = SparseXorKernel(self.matrix)
        self.packed_batch = PackedBatchGF2Kernel(self.matrix)
        self.packed_block = PackedBlockLUTKernel(self.matrix, block_width=self.block_width)
        self.event_update = EventUpdateKernel(self.matrix)

    def choose_backend(self, matrix: np.ndarray, workload: dict) -> object:
        """Return the backend selected by the simple rule baseline."""
        if require_gf2_matrix(matrix).shape != self.matrix.shape:
            raise ValueError("choose_backend matrix shape does not match planner matrix")
        workload_type = workload.get("type", "")
        if workload_type == "event_update":
            return self.event_update
        if workload_type == "single" and int(workload.get("hamming_weight", 0)) <= self.sparse_threshold:
            return self.sparse
        if int(workload.get("batch_size", 1)) >= self.batch_threshold:
            return self.packed_block
        return self.packed_block

    def apply(self, x: np.ndarray) -> np.ndarray:
        """Single-word syndrome/parity computation."""
        x = require_gf2_vector(x, self.n)
        if int(np.count_nonzero(x)) <= self.sparse_threshold:
            return self.sparse.apply(x)
        return self.packed_block.apply(x)

    def apply_many(self, x_batch: np.ndarray) -> np.ndarray:
        """Batch computation with a fixed rule-based backend choice."""
        x_batch = require_gf2_batch(x_batch, self.n)
        if x_batch.shape[0] >= self.batch_threshold:
            return self.packed_block.apply_many(x_batch)
        return self.packed_block.apply_many(x_batch)

    def apply_many_packed(self, x_batch: np.ndarray) -> np.ndarray:
        """Batch computation with packed ``np.uint16`` output when ``r <= 16``."""
        x_batch = require_gf2_batch(x_batch, self.n)
        return self.packed_block.apply_many_packed(x_batch)

    def update_many(
        self,
        current_values: np.ndarray,
        flipped_positions: np.ndarray,
    ) -> np.ndarray:
        """Batch event-driven update."""
        return self.event_update.update_many(current_values, flipped_positions)
