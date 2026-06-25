"""Correctness tests for benchmark workload helpers."""

from __future__ import annotations

import pytest

from benchmarks.bench_component_loop import check_component_loop_correctness
from benchmarks.bench_event_update import check_event_update_correctness


def test_component_loop_small_workload_is_bit_exact() -> None:
    pytest.importorskip("galois")

    assert check_component_loop_correctness(
        matrix_source="galois_systematic_candidate",
        num_words=8,
        chunk_words=4,
        density=0.05,
        block_width=8,
    )


@pytest.mark.parametrize("flip_count", [1, 2, 4])
def test_event_update_small_batch_matches_from_scratch(flip_count: int) -> None:
    pytest.importorskip("galois")

    assert check_event_update_correctness(
        matrix_source="galois_systematic_candidate",
        batch_size=16,
        flip_count=flip_count,
        density=0.05,
        block_width=8,
    )
