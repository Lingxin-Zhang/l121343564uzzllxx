"""Exact GF(2) linear-kernel backend interfaces."""

from .block_lut import BlockLUTKernel
from .cache_aware_planner import CacheAwarePlanner, CacheAwareSelection
from .event_update import EventUpdateKernel
from .naive import NaiveGF2Kernel
from .packed_batch import PackedBatchGF2Kernel
from .packed_block_lut import PackedBlockLUTKernel
from .planner import HybridPlanner
from .sparse_xor import SparseXorKernel

__all__ = [
    "BlockLUTKernel",
    "CacheAwarePlanner",
    "CacheAwareSelection",
    "EventUpdateKernel",
    "HybridPlanner",
    "NaiveGF2Kernel",
    "PackedBatchGF2Kernel",
    "PackedBlockLUTKernel",
    "SparseXorKernel",
]
