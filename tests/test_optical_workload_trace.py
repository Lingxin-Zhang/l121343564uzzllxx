"""Tests for clean-room optical-FEC-like workload traces."""

from __future__ import annotations

import pytest

from benchmarks.bench_optical_workloads import evaluate_optical_workload_with_breakdown
from codes.code_profiles import CodeProfile, get_code_profile
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
    assert trace.metadata["num_components_per_dimension"] == 4
    assert trace.metadata["num_blocks_meaning"] == "num_components_per_dimension"
    assert trace.num_syndrome_calls == 2 * 4 * 2
    assert trace.num_candidate_tests >= 0
    assert trace.num_event_updates >= 0


def test_staircase_like_trace_uses_half_block_window_component_count() -> None:
    profile = get_code_profile("ebch_256_239_r17")
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
    assert trace.metadata["active_blocks"] == 4
    assert trace.metadata["active_components"] == 4 * (profile.n // 2)
    assert trace.metadata["trace_model"] == "clean_room_half_block_window"
    update_events = [event for event in trace.events if event.event_type == "event_update.window"]
    assert {event.component_count for event in update_events} == {trace.metadata["active_components"]}


def test_staircase_like_rejects_odd_component_length() -> None:
    profile = CodeProfile(
        profile_name="odd_unit",
        n=255,
        r=16,
        matrix_source="unit",
        matrix_kind="unit",
        is_synthetic=True,
        verification_status="unit",
        notes="unit odd-length profile",
    )

    with pytest.raises(ValueError, match="even"):
        generate_trace(
            workload_type="staircase_like",
            profile=profile,
            num_blocks=8,
            window_len=4,
            num_iterations_or_steps=1,
        )


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
    candidate_event = next(event for event in trace.events if event.event_type == "candidate_test.component")
    assert candidate_event.candidates_per_component == 256
    assert candidate_event.intended_candidate_tests == 4 * 256
    assert candidate_event.executed_candidate_tests == 4 * 256
    assert trace.num_candidate_tests == 4 * 256
    assert trace.num_executed_candidate_tests == 4 * 256
    assert trace.intended_candidate_tests == 4 * 256
    assert trace.executed_candidate_tests == 4 * 256
    assert trace.intended_syndrome_calls == trace.executed_syndrome_calls
    assert trace.intended_event_updates == trace.executed_event_updates


def test_ofec_like_trace_records_candidate_cap_when_used() -> None:
    profile = get_code_profile("ebch_256_239_r17")
    trace = generate_trace(
        workload_type="ofec_like",
        profile=profile,
        num_blocks=4,
        window_len=2,
        num_iterations_or_steps=1,
        max_candidate_tests_per_event=32,
    )

    candidate_event = next(event for event in trace.events if event.event_type == "candidate_test.component")
    assert candidate_event.candidates_per_component == 256
    assert candidate_event.intended_candidate_tests == 4 * 256
    assert candidate_event.executed_candidate_tests == 32
    assert candidate_event.max_candidate_tests_per_event == 32
    assert trace.num_candidate_tests == 4 * 256
    assert trace.num_executed_candidate_tests == 32
    assert trace.intended_candidate_tests == 4 * 256
    assert trace.executed_candidate_tests == 32
    assert trace.executed_candidate_tests <= trace.intended_candidate_tests


def test_evaluate_optical_workload_runs_small_correctness_path() -> None:
    rows, breakdown_rows = evaluate_optical_workload_with_breakdown(
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
    assert all("intended_syndrome_calls" in row for row in rows)
    assert all("executed_syndrome_calls" in row for row in rows)
    assert all("intended_candidate_tests" in row for row in rows)
    assert all("executed_candidate_tests" in row for row in rows)
    assert all("intended_event_updates" in row for row in rows)
    assert all("executed_event_updates" in row for row in rows)
    assert all("aggregate_latency_per_executed_unit_us" in row for row in rows)
    assert all("throughput_Mexecuted_unit_s" in row for row in rows)
    assert all(
        int(row["executed_syndrome_calls"]) <= int(row["intended_syndrome_calls"])
        for row in rows
    )
    assert all(
        int(row["executed_candidate_tests"]) <= int(row["intended_candidate_tests"])
        for row in rows
    )
    assert all(
        int(row["executed_event_updates"]) <= int(row["intended_event_updates"])
        for row in rows
    )
    assert "Naive+EventUpdate.integrated" in {row["backend_or_method"] for row in rows}
    assert "EventUpdate.integrated" not in {row["backend_or_method"] for row in rows}
    assert breakdown_rows
    assert {"syndrome", "candidate_test", "event_update"} <= {
        row["task_kind"] for row in breakdown_rows
    }
    candidate_rows = [row for row in breakdown_rows if row["task_kind"] == "candidate_test"]
    assert candidate_rows
    assert {row["unit_type"] for row in candidate_rows} == {"candidate"}
