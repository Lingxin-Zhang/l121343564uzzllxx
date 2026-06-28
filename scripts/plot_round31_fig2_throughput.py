"""Plot Round 31 Fig. 2 as actual throughput, not speedup."""

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
DEFAULT_CSV = ROOT / "results" / "raw" / "round31_fixed_map_throughput.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round31_fig2_actual_throughput"
PROFILE = "bch_255_239_r16"
Y_LABEL = "Throughput (Mbit/s)"

DISPLAY_BACKEND = {
    "PackedBatchGF2Kernel.apply_many": "direct vectorized GF(2) matmul",
    "PackedBlockLUTKernel.apply_many_packed": "block-LUT (cache-aware)",
    "galois_per_codeword": "naive per-codeword",
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_true(value: object) -> bool:
    return str(value) == "True"


def load_points(path: Path = DEFAULT_CSV) -> list[dict[str, Any]]:
    rows = []
    for row in read_csv_rows(path):
        if row.get("profile") != PROFILE:
            continue
        if row.get("backend") not in DISPLAY_BACKEND:
            continue
        if not _is_true(row.get("timed")) or not _is_true(row.get("correctness_passed")):
            continue
        copied = dict(row)
        copied["batch_size"] = int(row["batch_size"])
        copied["throughput_Mbit_s"] = float(row["throughput_Mbit_s"])
        rows.append(copied)
    return rows


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 160,
        }
    )


def _save(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.7)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _annotate_peak(ax: plt.Axes, rows: list[dict[str, Any]], direct_by_batch: dict[int, float]) -> None:
    if not rows:
        return
    best = max(rows, key=lambda row: row["throughput_Mbit_s"])
    direct = direct_by_batch.get(best["batch_size"], 0.0)
    if direct <= 0:
        return
    speedup = best["throughput_Mbit_s"] / direct
    ax.annotate(
        f"{speedup:.2f}x @ {best['batch_size']:g}",
        (best["batch_size"], best["throughput_Mbit_s"]),
        textcoords="offset points",
        xytext=(6, 8),
        fontsize=7,
        color="#1f77b4",
    )


def plot_fig2(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    _setup_style()
    points = load_points(csv_path)
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for point in points:
        grouped[(point["task"], point["backend"])].append(point)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.9), sharey=False)
    colors = {
        "PackedBatchGF2Kernel.apply_many": "#555555",
        "PackedBlockLUTKernel.apply_many_packed": "#2AA6A1",
        "galois_per_codeword": "#999999",
    }
    styles = {
        "PackedBatchGF2Kernel.apply_many": "--",
        "PackedBlockLUTKernel.apply_many_packed": "-",
        "galois_per_codeword": ":",
    }
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome", "(b) Parity")):
        ax.axvspan(100, 10_000, color="#D9EAF7", alpha=0.35, label="100 to 1e4")
        direct_rows = sorted(grouped.get((task, "PackedBatchGF2Kernel.apply_many"), []), key=lambda r: r["batch_size"])
        direct_by_batch = {row["batch_size"]: row["throughput_Mbit_s"] for row in direct_rows}
        for backend in (
            "PackedBatchGF2Kernel.apply_many",
            "PackedBlockLUTKernel.apply_many_packed",
            "galois_per_codeword",
        ):
            rows = sorted(grouped.get((task, backend), []), key=lambda r: r["batch_size"])
            if not rows:
                continue
            ax.plot(
                [row["batch_size"] for row in rows],
                [row["throughput_Mbit_s"] for row in rows],
                marker="o" if backend != "galois_per_codeword" else "x",
                linestyle=styles[backend],
                linewidth=1.8 if backend == "PackedBlockLUTKernel.apply_many_packed" else 1.2,
                color=colors[backend],
                alpha=0.95 if backend != "galois_per_codeword" else 0.5,
                label=DISPLAY_BACKEND[backend],
            )
            if backend == "PackedBlockLUTKernel.apply_many_packed":
                _annotate_peak(ax, rows, direct_by_batch)
        ax.set_xscale("log")
        ax.set_title(title)
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel(Y_LABEL)
        ax.grid(True, which="both", alpha=0.24, linewidth=0.55)
        ax.tick_params(direction="out", length=3.5, width=0.8)
    handles, labels = axes[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=3, frameon=True, bbox_to_anchor=(0.5, 1.18))
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.24)
    _save(fig, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round 31 Fig. 2 actual throughput.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig2(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
