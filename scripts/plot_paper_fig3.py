"""Plot Fig. 3 from results/raw/block_width_cache_sweep.csv.

Required columns:
profile, task, backend, block_width, batch_size, timed, correctness_passed,
throughput_Mbit_s, input_width, lut_table_bytes, cache_level_fit.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "results" / "raw" / "block_width_cache_sweep.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "fig3_block_width_cache_sweep"
TASK = "syndrome"
PREFERRED_BATCH = 1000
BLOCK_WIDTH_LABEL = "Block width w (input bits per LUT block)"

CACHE_COLORS = {
    "L1": "#E8F5E9",
    "L2": "#E3F2FD",
    "L3": "#FFF3E0",
    "DRAM": "#FCE4EC",
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_true(value: object) -> bool:
    return str(value) == "True"


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
    fig.tight_layout(pad=0.7)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _peak_score(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    best_idx = max(range(len(values)), key=lambda idx: values[idx])
    if best_idx in (0, len(values) - 1):
        return 0.0
    edge = max(values[0], values[-1])
    return values[best_idx] - edge


def select_batch(rows: list[dict[str, Any]], profile: str) -> int:
    lut_rows = [
        row
        for row in rows
        if row["profile"] == profile
        and row["task"] == TASK
        and row["backend"] == "PackedBlockLUTKernel.apply_many_packed"
        and _is_true(row["timed"])
        and _is_true(row["correctness_passed"])
    ]
    batches = sorted({int(row["batch_size"]) for row in lut_rows})
    if PREFERRED_BATCH in batches:
        return PREFERRED_BATCH
    best_batch = batches[0]
    best_score = -1.0
    for batch in batches:
        values = [
            float(row["throughput_Mbit_s"])
            for row in sorted(
                (row for row in lut_rows if int(row["batch_size"]) == batch),
                key=lambda row: int(row["block_width"]),
            )
        ]
        score = _peak_score(values)
        if score > best_score:
            best_score = score
            best_batch = batch
    return best_batch


def load_panel_data(path: Path, profile: str) -> dict[str, Any]:
    rows = read_csv_rows(path)
    batch = select_batch(rows, profile)
    lut_rows = [
        row
        for row in rows
        if row["profile"] == profile
        and row["task"] == TASK
        and row["backend"] == "PackedBlockLUTKernel.apply_many_packed"
        and int(row["batch_size"]) == batch
        and _is_true(row["timed"])
        and _is_true(row["correctness_passed"])
    ]
    lut_rows = sorted(lut_rows, key=lambda row: int(row["block_width"]))
    direct_rows = [
        row
        for row in rows
        if row["profile"] == profile
        and row["task"] == TASK
        and row["backend"] == "PackedBatchGF2Kernel.apply_many"
        and int(row["batch_size"]) == batch
        and _is_true(row["timed"])
        and _is_true(row["correctness_passed"])
    ]
    if not lut_rows or not direct_rows:
        raise ValueError(f"missing timed rows for {profile} batch={batch}")
    direct = float(direct_rows[0]["throughput_Mbit_s"])
    return {
        "profile": profile,
        "batch_size": batch,
        "input_width": int(lut_rows[0]["input_width"]),
        "block_widths": [int(row["block_width"]) for row in lut_rows],
        "throughput": [float(row["throughput_Mbit_s"]) for row in lut_rows],
        "cache_levels": [row["cache_level_fit"] for row in lut_rows],
        "lut_bytes": [int(row["lut_table_bytes"]) for row in lut_rows],
        "direct_throughput": direct,
    }


def _span_edges(block_widths: list[int]) -> list[float]:
    if len(block_widths) == 1:
        return [block_widths[0] - 0.5, block_widths[0] + 0.5]
    mids = [(left + right) / 2 for left, right in zip(block_widths, block_widths[1:])]
    first = block_widths[0] - (mids[0] - block_widths[0])
    last = block_widths[-1] + (block_widths[-1] - mids[-1])
    return [first, *mids, last]


def _profile_title(profile: str) -> str:
    if profile == "bch_255_239_r16":
        return "(a) BCH(255,239), r=16"
    if profile == "bch_511_484_r27":
        return "(b) BCH(511,484), r=27"
    return profile


def _plot_panel(ax: plt.Axes, data: dict[str, Any], *, show_twin_ylabel: bool) -> None:
    block_widths = data["block_widths"]
    edges = _span_edges(block_widths)
    for idx, level in enumerate(data["cache_levels"]):
        ax.axvspan(
            edges[idx],
            edges[idx + 1],
            color=CACHE_COLORS.get(level, "#EEEEEE"),
            alpha=0.55,
            linewidth=0,
        )
    (line,) = ax.plot(
        block_widths,
        data["throughput"],
        marker="o",
        color="#1f77b4",
        linewidth=1.9,
        label="block-LUT (cache-aware)",
    )
    direct_line = ax.axhline(
        data["direct_throughput"],
        color="#444444",
        linestyle="--",
        linewidth=1.15,
        label="direct vectorized GF(2) matmul",
    )
    best_idx = max(range(len(data["throughput"])), key=lambda idx: data["throughput"][idx])
    best_a = block_widths[best_idx]
    best_y = data["throughput"][best_idx]
    ax.scatter([best_a], [best_y], s=46, color="#d62728", zorder=4, label="measured peak")
    ax.annotate(
        f"peak w={best_a}",
        (best_a, best_y),
        textcoords="offset points",
        xytext=(5, 8),
        fontsize=7.5,
        color="#8B1A1A",
    )
    ax.set_title(f"{_profile_title(data['profile'])}, batch={data['batch_size']}")
    ax.set_xlabel(BLOCK_WIDTH_LABEL)
    ax.set_ylabel("Throughput (Mbit/s)")
    ax.grid(True, alpha=0.24, linewidth=0.55)
    ax.tick_params(direction="out", length=3.5, width=0.8)
    ax.set_xticks(block_widths)

    twin = ax.twinx()
    operation_counts = [math.ceil(data["input_width"] / width) for width in block_widths]
    (ops_line,) = twin.plot(
        block_widths,
        operation_counts,
        marker="s",
        color="#2ca02c",
        linewidth=1.35,
        alpha=0.75,
        label="B=ceil(n/w)",
    )
    if show_twin_ylabel:
        twin.set_ylabel("LUT blocks per codeword B")
        twin.tick_params(direction="out", length=3.5, width=0.8)
    else:
        twin.set_ylabel("")
        twin.tick_params(direction="out", length=0, width=0, labelright=False, right=False)
    ax._round27_handles = [line, direct_line, ops_line]  # type: ignore[attr-defined]


def plot_fig3(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    _setup_style()
    fig, axes = plt.subplots(1, 2, figsize=(7.5, 3.05), sharey=False)
    panel_data = [
        load_panel_data(csv_path, "bch_255_239_r16"),
        load_panel_data(csv_path, "bch_511_484_r27"),
    ]
    for idx, (ax, data) in enumerate(zip(axes, panel_data)):
        _plot_panel(ax, data, show_twin_ylabel=idx == 1)

    cache_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.55, label=level)
        for level, color in CACHE_COLORS.items()
    ]
    line_handles = getattr(axes[0], "_round27_handles")
    fig.legend(
        [*line_handles, *cache_handles],
        [handle.get_label() for handle in [*line_handles, *cache_handles]],
        loc="upper center",
        ncol=4,
        frameon=True,
        bbox_to_anchor=(0.5, 1.22),
    )
    fig.subplots_adjust(top=0.74, bottom=0.17, wspace=0.34)
    _save_figure(fig, output_dir, OUTPUT_STEM)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot paper Fig. 3 from block-width CSV.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig3(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
