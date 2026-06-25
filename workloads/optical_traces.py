"""Clean-room trace generators for component-kernel workload benchmarks.

The traces model call patterns only. They are not full product-code,
staircase-code, oFEC, Chase-Pyndiah, BCH, or eBCH decoders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from codes.code_profiles import CodeProfile


@dataclass(frozen=True)
class TraceEvent:
    """One synthetic component-kernel call in a workload trace."""

    event_type: str
    component_count: int
    flip_count: int = 0
    candidate_count: int = 0
    notes: str = ""


@dataclass(frozen=True)
class WorkloadTrace:
    """A synthetic trace plus aggregate event counts."""

    workload_type: str
    profile_name: str
    events: tuple[TraceEvent, ...]
    num_blocks: int
    window_len: int
    num_iterations_or_steps: int
    metadata: dict[str, Any]

    @property
    def num_syndrome_calls(self) -> int:
        return sum(event.component_count for event in self.events if event.event_type.startswith("syndrome_batch"))

    @property
    def num_candidate_tests(self) -> int:
        return sum(event.candidate_count for event in self.events if event.event_type.startswith("candidate_test"))

    @property
    def num_event_updates(self) -> int:
        return sum(event.component_count for event in self.events if event.event_type.startswith("event_update"))


def generate_trace(
    *,
    workload_type: str,
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_iterations_or_steps: int,
) -> WorkloadTrace:
    """Generate one deterministic trace for a named workload type."""

    workload_type = workload_type.strip()
    num_blocks = _require_positive_int(num_blocks, "num_blocks")
    window_len = _require_positive_int(window_len, "window_len")
    num_iterations_or_steps = _require_positive_int(
        num_iterations_or_steps,
        "num_iterations_or_steps",
    )
    if workload_type == "product_like":
        return _product_like(profile, num_blocks, window_len, num_iterations_or_steps)
    if workload_type == "staircase_like":
        return _staircase_like(profile, num_blocks, window_len, num_iterations_or_steps)
    if workload_type == "ofec_like":
        return _ofec_like(profile, num_blocks, window_len, num_iterations_or_steps)
    raise ValueError("workload_type must be product_like, staircase_like, or ofec_like")


def _product_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_iterations: int,
) -> WorkloadTrace:
    events: list[TraceEvent] = []
    for _ in range(num_iterations):
        events.append(TraceEvent("syndrome_batch.row", num_blocks, notes="row components"))
        events.append(TraceEvent("syndrome_batch.column", num_blocks, notes="column components"))
    return WorkloadTrace(
        workload_type="product_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_iterations,
        metadata={"layout": "row_column"},
    )


def _staircase_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_steps: int,
) -> WorkloadTrace:
    events: list[TraceEvent] = []
    active_components = max(1, min(num_blocks, window_len) * 2)
    for _ in range(num_steps):
        events.append(
            TraceEvent(
                "syndrome_batch.window",
                active_components,
                notes="sliding-window component batch",
            )
        )
        events.append(
            TraceEvent(
                "event_update.window",
                active_components,
                flip_count=2,
                notes="small active-window flip update",
            )
        )
    return WorkloadTrace(
        workload_type="staircase_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_steps,
        metadata={"half_width": profile.n // 2, "active_components": active_components},
    )


def _ofec_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_steps: int,
) -> WorkloadTrace:
    events: list[TraceEvent] = []
    component_count = max(1, num_blocks)
    for _ in range(num_steps):
        events.append(TraceEvent("syndrome_batch.component", component_count))
        events.append(
            TraceEvent(
                "candidate_test.component",
                component_count,
                candidate_count=256,
                notes="candidate pattern kernel calls only",
            )
        )
        events.append(
            TraceEvent(
                "event_update.component",
                component_count,
                flip_count=2,
                notes="event update after candidate selection",
            )
        )
    return WorkloadTrace(
        workload_type="ofec_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_steps,
        metadata={"component_kernel_workload": True},
    )


def _require_positive_int(value: int, name: str) -> int:
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value
