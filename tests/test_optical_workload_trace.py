"""Tests for clean-room optical-FEC-like workload traces."""

from __future__ import annotations

from benchmarks.bench_optical_workloads import evaluate_optical_workload
from codes.code_profiles import get_code_profile
from workloads.optical_traces import generate_trace


def test_product_like_trace_has_row_and_column_syndrome_events() -> None:
    profile = get_code_profile("bch_255_239_r16")
    trace = generate_trace(
        workload_type="product_like",
        profile=profile,
        num_blocks=4,
        window_len=2,
        num_iterations_or_steps=2,
    )

    event_names = [event.event_type for event in trace.events]
    assert "syndrome_batch.row" in event_names
    assert "syndrome_batch.column" in event_names
    assert trace.num_syndrome_calls > 0
    assert trace.num_candidate_tests >= 0
    assert trace.num_event_updates >= 0


def test_staircase_like_trace_has_window_and_event_updates() -> None:
    profile = get_code_profile("bch_255_239_r16")
    trace = generate_trace(
        workload_type="staircase_like",
        profile=profile,
        num_blocks=8,
        window_len=4,
        num_iterations_or_steps=2,
    )

    event_names = [event.event_type for event in trace.events]
    assert "syndrome_batch.window" in event_names
    assert "event_update.window" in event_names
    assert trace.metadata["half_width"] == profile.n // 2


def test_ofec_like_trace_contains_syndrome_candidate_and_event_update() -> None:
    profile = get_code_profile("ebch_256_239_r17")
    trace = generate_trace(
        workload_type="ofec_like",
        profile=profile,
        num_blocks=4,
        window_len=2,
        num_iterations_or_steps=1,
    )

    event_names = {event.event_type for event in trace.events}
    assert {"syndrome_batch.component", "candidate_test.component", "event_update.component"} <= event_names


def test_evaluate_optical_workload_runs_small_correctness_path() -> None:
    rows = evaluate_optical_workload(
        workload_type="ofec_like",
        code_profile="ebch_256_239_r17",
        num_blocks=2,
        window_len=2,
        num_iterations_or_steps=1,
        density=0.05,
        batch_size=4,
        block_width=4,
        repeats=1,
        preset="unit",
    )

    assert rows
    assert all(row["correctness_passed"] is True for row in rows)
    assert all("BER" not in row for row in rows)
