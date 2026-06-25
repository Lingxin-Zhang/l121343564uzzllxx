"""Export compact paper-style figures from summary CSV files."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SUMMARY_DIR = ROOT / "results" / "summary"
OUTPUT_DIR = ROOT / "results" / "paper_figures"


def read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing summary CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_figure(fig: plt.Figure, output_dir: Path, name: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.35)
    for suffix in ("png", "pdf"):
        output = output_dir / f"{name}.{suffix}"
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def setup_axes(title: str, xlabel: str, ylabel: str) -> tuple[plt.Figure, plt.Axes]:
    plt.rcParams.update(
        {
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "legend.fontsize": 6,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, ax = plt.subplots(figsize=(3.5, 2.45))
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.22, linewidth=0.6)
    return fig, ax


def plot_bch_syndrome(summary_dir: Path, output_dir: Path) -> None:
    rows = [
        row
        for row in read_csv(summary_dir / "bch_syndrome_summary.csv")
        if row["matrix_source"] == "galois_systematic_candidate"
    ]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[f"{row['backend']} | iter={row['iterations']}"].append(row)
    fig, ax = setup_axes(
        "Component syndrome throughput",
        "total_bits",
        "Mbit/s",
    )
    for label, label_rows in sorted(grouped.items()):
        ordered = sorted(label_rows, key=lambda row: float(row["total_bits"]))
        ax.plot(
            [float(row["total_bits"]) for row in ordered],
            [float(row["mean_throughput_Mbit_s"]) for row in ordered],
            marker="o",
            linewidth=1.2,
            markersize=3,
            label=label,
        )
    ax.set_xscale("log")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    save_figure(fig, output_dir, "fig_bch_syndrome_throughput")


def plot_component_loop(summary_dir: Path, output_dir: Path) -> None:
    rows = read_csv(summary_dir / "component_loop_summary.csv")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["backend"]].append(row)
    fig, ax = setup_axes(
        "Repeated component-kernel loop",
        "num_words",
        "latency / word (us)",
    )
    for label, label_rows in sorted(grouped.items()):
        point_by_x: dict[float, list[float]] = defaultdict(list)
        for row in label_rows:
            point_by_x[float(row["num_words"])].append(
                float(row["mean_latency_per_word_us"])
            )
        x = []
        y = []
        for num_words, values in sorted(point_by_x.items()):
            x.append(num_words)
            y.append(sum(values) / len(values))
        ax.plot(x, y, marker="o", linewidth=1.2, markersize=3, label=label)
    ax.set_xscale("log", base=2)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    save_figure(fig, output_dir, "fig_component_loop_latency")


def plot_event_update(summary_dir: Path, output_dir: Path) -> None:
    rows = read_csv(summary_dir / "event_update_summary.csv")
    methods = {
        "from_scratch.PackedBlockLUT.apply_many_packed",
        "event_update.loop_update",
        "event_update.batch_update_many",
    }
    grouped: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if row["method"] not in methods:
            continue
        grouped[row["method"]][float(row["flip_count"])].append(
            float(row["mean_latency_per_word_us"])
        )
    fig, ax = setup_axes(
        "Event-driven syndrome update",
        "flip_count",
        "latency / word (us)",
    )
    for label, by_flip in sorted(grouped.items()):
        x = []
        y = []
        for flip_count, values in sorted(by_flip.items()):
            x.append(flip_count)
            y.append(sum(values) / len(values))
        ax.plot(x, y, marker="o", linewidth=1.2, markersize=3, label=label)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    save_figure(fig, output_dir, "fig_event_update_comparison")


def plot_planner(summary_dir: Path, output_dir: Path) -> None:
    rows = [
        row
        for row in read_csv(summary_dir / "planner_summary.csv")
        if row["workload_type"] == "event_update"
    ]
    grouped: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["backend_or_method"]][float(row["batch_size"])].append(
            float(row["mean_latency_per_word_us"])
        )
    fig, ax = setup_axes(
        "Rule-based backend dispatcher",
        "batch_size",
        "latency / word (us)",
    )
    for label, by_batch in sorted(grouped.items()):
        x = []
        y = []
        for batch_size, values in sorted(by_batch.items()):
            x.append(batch_size)
            y.append(sum(values) / len(values))
        ax.plot(x, y, marker="o", linewidth=1.2, markersize=3, label=label)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    save_figure(fig, output_dir, "fig_planner_latency")


def export_all(summary_dir: Path, output_dir: Path) -> None:
    plot_bch_syndrome(summary_dir, output_dir)
    plot_component_loop(summary_dir, output_dir)
    plot_event_update(summary_dir, output_dir)
    plot_planner(summary_dir, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export compact paper-style figures.")
    parser.add_argument("--summary-dir", type=Path, default=SUMMARY_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    export_all(args.summary_dir, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
