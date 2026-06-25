"""Synthetic workload helpers for GF(2) benchmark drivers."""

from .candidate_patterns import make_chase_ii_patterns, make_fixed_weight_patterns
from .optical_traces import TraceEvent, WorkloadTrace, generate_trace

__all__ = [
    "TraceEvent",
    "WorkloadTrace",
    "generate_trace",
    "make_chase_ii_patterns",
    "make_fixed_weight_patterns",
]
