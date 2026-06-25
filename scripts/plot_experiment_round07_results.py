"""Generate diagnostic figures for experiment round 07 planner calibration."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_DIR = ROOT / "results" / "summary"
FIGURE_DIR = ROOT / "results" / "figures"
FIGURE_NAME = "experiment_round07_cache_aware_calibration"
COLOR_MEAN = "#0072B2"
COLOR_P90 = "#D55E00"
COLOR_EXACT = "#009E73"
COLOR_BACKEND = "#CC79A7"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(row: dict[str, Any], key: str, default: float = float("nan")) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def plot_cache_aware_calibration(
    *,
    summary_path: Path = SUMMARY_DIR / "cache_aware_selection_workload_summary.csv",
    figure_dir: Path = FIGURE_DIR,
) -> None:
    """Plot workload-level planner/oracle ratio and match rates."""
    rows = _read_csv(summary_path)
    workload_order = [
        "sparse_single",
        "dense_batch",
        "candidate_test_packed",
        "component_decode_batch",
        "event_update",
    ]
    presets = sorted({row["preset"] for row in rows})
    preferred_preset = "paper" if "paper" in presets else ("paper-small" if "paper-small" in presets else presets[-1])
    selected_rows = [row for row in rows if row["preset"] == preferred_preset]
    workloads = [
        workload
        for workload in workload_order
        if any(row["workload_type"] == workload for row in selected_rows)
    ]
    if not workloads:
        raise ValueError("no workload rows available for plotting")

    by_workload = {row["workload_type"]: row for row in selected_rows}
    x = np.arange(len(workloads), dtype=float)
    mean_ratio = [_float(by_workload[workload], "mean_planner_over_oracle") for workload in workloads]
    p90_ratio = [_float(by_workload[workload], "p90_planner_over_oracle") for workload in workloads]
    exact_match = [
        _float(by_workload[workload], "oracle_match_rate_backend_and_block")
        for workload in workloads
    ]
    backend_match = [
        _float(by_workload[workload], "oracle_match_rate_backend_only")
        for workload in workloads
    ]

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.8), sharex=True)
    axes[0].plot(x, mean_ratio, marker="o", linewidth=1.8, color=COLOR_MEAN, label="mean")
    axes[0].plot(x, p90_ratio, marker="s", linewidth=1.8, color=COLOR_P90, label="p90")
    axes[0].axhline(1.0, color="#333333", linewidth=1.0, linestyle="--")
    axes[0].set_ylabel("Planner / oracle latency")
    axes[0].set_title(f"Latency ratio ({preferred_preset})")
    axes[0].grid(True, axis="y", alpha=0.25, linestyle="--")
    axes[0].legend(frameon=False)

    axes[1].plot(
        x,
        exact_match,
        marker="o",
        linewidth=1.8,
        color=COLOR_EXACT,
        label="backend + block",
    )
    axes[1].plot(
        x,
        backend_match,
        marker="s",
        linewidth=1.8,
        color=COLOR_BACKEND,
        label="backend only",
    )
    axes[1].set_ylim(-0.05, 1.05)
    axes[1].set_ylabel("Oracle match rate")
    axes[1].set_title("Selection agreement")
    axes[1].grid(True, axis="y", alpha=0.25, linestyle="--")
    axes[1].legend(frameon=False)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(workloads, rotation=25, ha="right")
        ax.set_xlabel("workload_type")

    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        output = figure_dir / f"{FIGURE_NAME}.{suffix}"
        fig.savefig(output, dpi=240, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def main() -> None:
    plot_cache_aware_calibration()


if __name__ == "__main__":
    main()
