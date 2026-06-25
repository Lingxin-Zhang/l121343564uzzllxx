"""Generate diagnostic figures for supplemental experiment round 02."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
FIGURE_DIR = ROOT / "results" / "figures"

COLORS = [
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
]
MARKERS = ["o", "s", "^", "D", "v", "P"]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        output = FIGURE_DIR / f"{name}.{suffix}"
        fig.savefig(output, dpi=240, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def plot_candidate_testing() -> None:
    rows = _read_csv(RAW_DIR / "candidate_testing.csv")
    grouped: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        backend = row["backend"]
        count = int(float(row["candidate_count"]))
        latency = float(row["latency_per_candidate_us"])
        grouped[backend][count].append(latency)

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for index, (backend, count_map) in enumerate(sorted(grouped.items())):
        ordered_counts = sorted(count_map)
        ax.plot(
            ordered_counts,
            [_mean(count_map[count]) for count in ordered_counts],
            marker=MARKERS[index % len(MARKERS)],
            linewidth=1.7,
            markersize=5,
            color=COLORS[index % len(COLORS)],
            label=backend,
        )
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xlabel("candidate_count")
    ax.set_ylabel("Latency per candidate (us)")
    ax.set_title("Candidate testing diagnostic")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    _save(fig, "experiment_round02_candidate_testing")


def plot_optical_workloads() -> None:
    rows = _read_csv(RAW_DIR / "optical_workloads.csv")
    workload_types = sorted({row["workload_type"] for row in rows})
    methods = sorted({row["backend_or_method"] for row in rows})
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["workload_type"], row["backend_or_method"])].append(
            float(row["latency_per_component_us"])
        )

    x = np.arange(len(workload_types), dtype=float)
    width = 0.78 / max(1, len(methods))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for index, method in enumerate(methods):
        offsets = x - 0.39 + width / 2 + index * width
        values = [_mean(grouped[(workload, method)]) for workload in workload_types]
        ax.bar(
            offsets,
            values,
            width=width,
            label=method,
            color=COLORS[index % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(workload_types, rotation=15, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel("workload_type")
    ax.set_ylabel("Latency per component (us)")
    ax.set_title("Trace-level workload diagnostic")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    _save(fig, "experiment_round02_optical_workloads")


def plot_optical_workload_breakdown() -> None:
    rows = _read_csv(RAW_DIR / "optical_workload_breakdown.csv")
    task_kinds = ["syndrome", "candidate_test", "event_update"]
    methods = sorted({row["backend_or_method"] for row in rows})
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["task_kind"], row["backend_or_method"])].append(
            float(row["latency_per_unit_us"])
        )

    x = np.arange(len(task_kinds), dtype=float)
    width = 0.78 / max(1, len(methods))
    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    for index, method in enumerate(methods):
        offsets = x - 0.39 + width / 2 + index * width
        values = [_mean(grouped[(task_kind, method)]) for task_kind in task_kinds]
        ax.bar(
            offsets,
            values,
            width=width,
            label=method,
            color=COLORS[index % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )
    ax.set_xticks(x)
    ax.set_xticklabels(task_kinds, rotation=15, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel("task_kind")
    ax.set_ylabel("Latency per task unit (us)")
    ax.set_title("Trace-level task breakdown diagnostic")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    _save(fig, "experiment_round02_optical_workload_breakdown")


def main() -> None:
    plot_candidate_testing()
    plot_optical_workloads()
    plot_optical_workload_breakdown()


if __name__ == "__main__":
    main()
