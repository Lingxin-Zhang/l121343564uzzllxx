"""Plot Fig. 2 from results/raw/fixed_map_three_backend.csv.

Required columns:
profile, task, backend, batch_size, timed, correctness_passed,
throughput_Mbit_s.
"""

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
DEFAULT_CSV = ROOT / "results" / "raw" / "fixed_map_three_backend.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "fig2_fixed_map_speedup"
PROFILE = "bch_255_239_r16"

DISPLAY_BACKEND = {
    "PackedBatchGF2Kernel.apply_many": "direct vectorized GF(2) matmul",
    "PackedBlockLUTKernel.apply_many_packed": "block-LUT (cache-aware)",
    "galois_per_codeword": "naive per-codeword",
}

TASK_TITLES = {
    "syndrome": "(a) Syndrome",
    "parity": "(b) Parity",
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_true(value: object) -> bool:
    return str(value) == "True"


def load_fig2_points(path: Path = DEFAULT_CSV) -> list[dict[str, Any]]:
    """Return timed Fig. 2 points with speedup against direct vectorized matmul."""

    rows = [
        row
        for row in read_csv_rows(path)
        if row["profile"] == PROFILE
        and row["backend"] in DISPLAY_BACKEND
        and _is_true(row["timed"])
        and _is_true(row["correctness_passed"])
    ]
    direct_by_task_batch: dict[tuple[str, int], float] = {}
    for row in rows:
        if row["backend"] == "PackedBatchGF2Kernel.apply_many":
            direct_by_task_batch[(row["task"], int(row["batch_size"]))] = float(
                row["throughput_Mbit_s"]
            )

    points: list[dict[str, Any]] = []
    for row in rows:
        batch = int(row["batch_size"])
        key = (row["task"], batch)
        direct = direct_by_task_batch.get(key)
        if not direct or direct <= 0:
            continue
        copied = dict(row)
        copied["batch_size"] = batch
        copied["throughput_Mbit_s"] = float(row["throughput_Mbit_s"])
        copied["speedup_vs_direct"] = copied["throughput_Mbit_s"] / direct
        copied["timed"] = True
        points.append(copied)
    return points


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "figure.dpi": 160,
        }
    )


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.6)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def plot_fig2(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    _setup_style()
    points = load_fig2_points(csv_path)
    by_task_backend: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        by_task_backend[(point["task"], point["backend"])].append(point)

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.85), sharey=True)
    colors = {
        "PackedBlockLUTKernel.apply_many_packed": "#1f77b4",
        "galois_per_codeword": "#777777",
    }
    markers = {
        "PackedBlockLUTKernel.apply_many_packed": "o",
        "galois_per_codeword": "x",
    }

    for ax, task in zip(axes, ("syndrome", "parity")):
        ax.axhline(1.0, color="#444444", linestyle="--", linewidth=1.1, label="1x baseline")
        ax.axvspan(100, 100_000, color="#D9EAF7", alpha=0.45, label="100 to 1e5")
        for backend in ("PackedBlockLUTKernel.apply_many_packed", "galois_per_codeword"):
            rows = sorted(by_task_backend.get((task, backend), []), key=lambda row: row["batch_size"])
            if not rows:
                continue
            x = [row["batch_size"] for row in rows]
            y = [row["speedup_vs_direct"] for row in rows]
            ax.plot(
                x,
                y,
                marker=markers[backend],
                linewidth=1.8 if backend != "galois_per_codeword" else 1.0,
                markersize=4.2,
                color=colors[backend],
                alpha=1.0 if backend != "galois_per_codeword" else 0.45,
                label=DISPLAY_BACKEND[backend],
            )
            if backend == "PackedBlockLUTKernel.apply_many_packed":
                for row in rows:
                    ax.annotate(
                        f"{row['throughput_Mbit_s']:.0f}",
                        (row["batch_size"], row["speedup_vs_direct"]),
                        textcoords="offset points",
                        xytext=(0, 6),
                        ha="center",
                        fontsize=6.5,
                        color=colors[backend],
                    )
        ax.set_xscale("log")
        ax.set_title(TASK_TITLES[task])
        ax.set_xlabel("Batch size (codewords)")
        ax.grid(True, which="both", alpha=0.24, linewidth=0.55)
        ax.margins(y=0.16)
        ax.tick_params(direction="out", length=3.5, width=0.8)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
    axes[0].set_ylabel("Speedup vs direct vectorized GF(2) matmul")
    axes[1].text(
        0.98,
        0.04,
        "Point labels: block-LUT Mbit/s",
        transform=axes[1].transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color="#444444",
    )
    handles, labels = axes[0].get_legend_handles_labels()
    unique: dict[str, Any] = {}
    for handle, label in zip(handles, labels):
        unique.setdefault(label, handle)
    fig.legend(
        unique.values(),
        unique.keys(),
        loc="upper center",
        ncol=3,
        frameon=True,
        bbox_to_anchor=(0.5, 1.17),
    )
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.16)
    _save_figure(fig, output_dir, OUTPUT_STEM)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot paper Fig. 2 from fixed-map CSV.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig2(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
