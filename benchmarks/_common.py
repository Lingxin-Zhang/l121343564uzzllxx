"""Shared helpers for reproducible micro-benchmarks."""

from __future__ import annotations

import csv
import statistics
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
FIGURE_DIR = ROOT / "results" / "figures"

N = 255
R = 16
MATRIX_SEED = 20260628


def ensure_result_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)


def make_matrix() -> np.ndarray:
    rng = np.random.default_rng(MATRIX_SEED)
    return rng.integers(0, 2, size=(N, R), dtype=np.uint8)


def make_batch(
    rng: np.random.Generator,
    batch_size: int,
    density: float,
    n: int = N,
) -> np.ndarray:
    return (rng.random((batch_size, n)) < density).astype(np.uint8)


def time_repeats(
    fn: Callable[[], Any],
    repeats: int,
    warmups: int = 1,
) -> list[float]:
    for _ in range(warmups):
        fn()

    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def summarize_per_word(samples: list[float], words_per_call: int) -> dict[str, float]:
    per_word = [sample / words_per_call for sample in samples]
    mean = statistics.fmean(per_word)
    std = statistics.stdev(per_word) if len(per_word) > 1 else 0.0
    return {
        "latency_per_word_us": mean * 1_000_000.0,
        "throughput_words_per_sec": (1.0 / mean) if mean > 0 else 0.0,
        "mean": mean,
        "std": std,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no benchmark rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def block_lut_table_size_bytes(kernel: Any) -> int:
    return int(sum(table.nbytes for _, _, _, table in kernel.blocks))


def mark_fastest(rows: Iterable[dict[str, Any]], group_key: str) -> list[dict[str, Any]]:
    grouped: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row[group_key], []).append(row)

    marked = []
    for group_rows in grouped.values():
        best = min(float(row["latency_per_word_us"]) for row in group_rows)
        for row in group_rows:
            copied = dict(row)
            copied["is_fastest"] = float(row["latency_per_word_us"]) == best
            marked.append(copied)
    return marked
