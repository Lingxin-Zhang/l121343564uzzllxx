"""Generate diagnostic figures for supplemental experiment round 06."""

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
FIGURE_NAME = "experiment_round06_cache_aware_selection"
COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def plot_cache_aware_selection(
    *,
    csv_path: Path = RAW_DIR / "cache_aware_selection.csv",
    figure_dir: Path = FIGURE_DIR,
) -> None:
    rows = _read_csv(csv_path)
    workload_order = [
        "sparse_single",
        "dense_batch",
        "candidate_test_packed",
        "component_decode_batch",
        "event_update",
    ]
    workloads = [name for name in workload_order if any(row["workload_type"] == name for row in rows)]
    backends = sorted({row["selected_backend"] for row in rows})
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["workload_type"], row["selected_backend"])].append(
            float(row["planner_over_oracle"])
        )

    x = np.arange(len(workloads), dtype=float)
    width = 0.78 / max(1, len(backends))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for index, backend in enumerate(backends):
        offsets = x - 0.39 + width / 2 + index * width
        values = [_mean(grouped[(workload, backend)]) for workload in workloads]
        ax.bar(
            offsets,
            values,
            width=width,
            label=backend,
            color=COLORS[index % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
        )
    ax.axhline(1.0, color="#333333", linewidth=1.0, linestyle="--", label="oracle parity")
    ax.set_xticks(x)
    ax.set_xticklabels(workloads, rotation=20, ha="right")
    ax.set_ylabel("Planner / oracle latency")
    ax.set_xlabel("workload_type")
    ax.set_title("Cache-aware selection diagnostic")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)

    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        output = figure_dir / f"{FIGURE_NAME}.{suffix}"
        fig.savefig(output, dpi=240, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def main() -> None:
    plot_cache_aware_selection()


if __name__ == "__main__":
    main()
