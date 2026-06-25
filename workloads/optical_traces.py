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
    candidates_per_component: int = 0
    intended_candidate_tests: int = 0
    executed_candidate_tests: int = 0
    max_candidate_tests_per_event: int = 0
    notes: str = ""

    @property
    def candidate_count(self) -> int:
        """Backward-compatible alias for candidates per component."""

        return self.candidates_per_component


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
        return sum(
            event.intended_candidate_tests
            for event in self.events
            if event.event_type.startswith("candidate_test")
        )

    @property
    def num_executed_candidate_tests(self) -> int:
        return sum(
            event.executed_candidate_tests
            for event in self.events
            if event.event_type.startswith("candidate_test")
        )

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
    max_candidate_tests_per_event: int | None = None,
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
        return _ofec_like(
            profile,
            num_blocks,
            window_len,
            num_iterations_or_steps,
            max_candidate_tests_per_event=max_candidate_tests_per_event,
        )
    raise ValueError("workload_type must be product_like, staircase_like, or ofec_like")


def _product_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_iterations: int,
) -> WorkloadTrace:
    num_components_per_dimension = num_blocks
    events: list[TraceEvent] = []
    for _ in range(num_iterations):
        events.append(
            TraceEvent(
                "syndrome_batch.row",
                num_components_per_dimension,
                notes="row components; num_blocks means num_components_per_dimension",
            )
        )
        events.append(
            TraceEvent(
                "syndrome_batch.column",
                num_components_per_dimension,
                notes="column components; num_blocks means num_components_per_dimension",
            )
        )
    return WorkloadTrace(
        workload_type="product_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_iterations,
        metadata={
            "layout": "row_column",
            "num_blocks_meaning": "num_components_per_dimension",
            "num_components_per_dimension": num_components_per_dimension,
            "trace_model": "clean_room_row_column_components",
        },
    )


def _staircase_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_steps: int,
) -> WorkloadTrace:
    if profile.n % 2:
        raise ValueError("staircase_like requires an even component length n")
    events: list[TraceEvent] = []
    half_width = profile.n // 2
    active_blocks = min(num_blocks, window_len)
    active_components = active_blocks * half_width
    for _ in range(num_steps):
        events.append(
            TraceEvent(
                "syndrome_batch.window",
                active_components,
                notes="sliding-window component batch; trace-level workload only",
            )
        )
        events.append(
            TraceEvent(
                "event_update.window",
                active_components,
                flip_count=2,
                notes="small active-window flip update; trace-level workload only",
            )
        )
    return WorkloadTrace(
        workload_type="staircase_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_steps,
        metadata={
            "half_width": half_width,
            "active_blocks": active_blocks,
            "active_components": active_components,
            "trace_model": "clean_room_half_block_window",
        },
    )


def _ofec_like(
    profile: CodeProfile,
    num_blocks: int,
    window_len: int,
    num_steps: int,
    *,
    max_candidate_tests_per_event: int | None,
) -> WorkloadTrace:
    events: list[TraceEvent] = []
    component_count = max(1, num_blocks)
    candidates_per_component = 256
    cap = _optional_positive_int(max_candidate_tests_per_event, "max_candidate_tests_per_event")
    for _ in range(num_steps):
        events.append(TraceEvent("syndrome_batch.component", component_count))
        intended_candidate_tests = component_count * candidates_per_component
        executed_candidate_tests = (
            intended_candidate_tests if cap is None else min(intended_candidate_tests, cap)
        )
        events.append(
            TraceEvent(
                "candidate_test.component",
                component_count,
                candidates_per_component=candidates_per_component,
                intended_candidate_tests=intended_candidate_tests,
                executed_candidate_tests=executed_candidate_tests,
                max_candidate_tests_per_event=cap or 0,
                notes=(
                    "candidate pattern kernel calls only; trace-level workload only; "
                    "no BER; no full decoder"
                ),
            )
        )
        events.append(
            TraceEvent(
                "event_update.component",
                component_count,
                flip_count=2,
                notes="event update after candidate selection; trace-level workload only",
            )
        )
    return WorkloadTrace(
        workload_type="ofec_like",
        profile_name=profile.profile_name,
        events=tuple(events),
        num_blocks=num_blocks,
        window_len=window_len,
        num_iterations_or_steps=num_steps,
        metadata={
            "component_kernel_workload": True,
            "candidates_per_component": candidates_per_component,
            "trace_model": "clean_room_component_candidate_update",
            "notes": "trace-level workload only; no BER; no full decoder",
        },
    )


def _require_positive_int(value: int, name: str) -> int:
    value = int(value)
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _optional_positive_int(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    return _require_positive_int(value, name)
