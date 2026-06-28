"""Plot Round 31 Fig. 3 cache-width sweep."""

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
DEFAULT_CSV = ROOT / "results" / "raw" / "round31_block_width_cache_sweep.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round31_fig3_cache_width"
TASK = "syndrome"
PREFERRED_BATCH = 1000

CACHE_COLORS = {
    "L1": "#E8F5E9",
    "L2": "#E3F2FD",
    "L3": "#FFF3E0",
    "DRAM": "#FCE4EC",
}

PROFILE_TITLES = {
    "bch_255_239_r16": "BCH(255,239), r=16",
    "bch_255_231_r24": "BCH(255,231), r=24",
    "bch_511_484_r27": "BCH(511,484), r=27",
    "bch_1023_993_r30": "BCH(1023,993), r=30",
}


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_true(value: object) -> bool:
    return str(value) == "True"


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "legend.fontsize": 7.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "figure.dpi": 160,
        }
    )


def _save(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _select_batch(rows: list[dict[str, Any]]) -> int:
    batches = sorted({int(row["batch_size"]) for row in rows})
    if PREFERRED_BATCH in batches:
        return PREFERRED_BATCH
    return batches[0]


def load_panel_rows(path: Path = DEFAULT_CSV) -> dict[str, list[dict[str, Any]]]:
    rows = [
        row
        for row in read_csv_rows(path)
        if row.get("task") == TASK
        and row.get("measurement_mode", "natural") == "natural"
        and row.get("backend") == "PackedBlockLUTKernel.apply_many_packed"
        and _is_true(row.get("timed"))
        and _is_true(row.get("correctness_passed"))
    ]
    by_profile_batch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in sorted({row["profile"] for row in rows}):
        profile_rows = [row for row in rows if row["profile"] == profile]
        if not profile_rows:
            continue
        batch = _select_batch(profile_rows)
        selected = [row for row in profile_rows if int(row["batch_size"]) == batch]
        by_profile_batch[profile] = sorted(selected, key=lambda row: int(row["block_width"]))
    return dict(by_profile_batch)


def _span_edges(widths: list[int]) -> list[float]:
    if len(widths) == 1:
        return [widths[0] - 0.5, widths[0] + 0.5]
    mids = [(a + b) / 2 for a, b in zip(widths, widths[1:])]
    return [widths[0] - (mids[0] - widths[0]), *mids, widths[-1] + (widths[-1] - mids[-1])]


def _plot_panel(ax: plt.Axes, profile: str, rows: list[dict[str, Any]], *, show_right_label: bool) -> None:
    widths = [int(row["block_width"]) for row in rows]
    throughput = [float(row["throughput_Mbit_s"]) for row in rows]
    min_y = [float(row.get("min_runtime_s", 0.0)) for row in rows]
    median_y = [float(row.get("median_runtime_s", 0.0)) for row in rows]
    max_y = [float(row.get("max_runtime_s", 0.0)) for row in rows]
    yerr = [
        [max(0.0, t - (t * med / mx if mx > 0 else t)) for t, mx, med in zip(throughput, max_y, median_y)],
        [max(0.0, (t * med / mn if mn > 0 else t) - t) for t, mn, med in zip(throughput, min_y, median_y)],
    ]
    edges = _span_edges(widths)
    for idx, row in enumerate(rows):
        ax.axvspan(edges[idx], edges[idx + 1], color=CACHE_COLORS.get(row["cache_level_fit"], "#EEEEEE"), alpha=0.48)
    ax.errorbar(
        widths,
        throughput,
        yerr=yerr,
        marker="o",
        linewidth=1.65,
        color="#2AA6A1",
        ecolor="#666666",
        elinewidth=0.7,
        capsize=2.0,
        label="measured throughput",
    )
    best = max(rows, key=lambda row: float(row["throughput_Mbit_s"]))
    ax.scatter([int(best["block_width"])], [float(best["throughput_Mbit_s"])], color="#8B1A1A", s=34, zorder=4)
    ax.annotate(
        f"best w={best['block_width']}",
        (int(best["block_width"]), float(best["throughput_Mbit_s"])),
        textcoords="offset points",
        xytext=(4, 7),
        fontsize=7,
        color="#8B1A1A",
    )
    ax.set_title(f"{PROFILE_TITLES.get(profile, profile)}, batch={rows[0]['batch_size']}")
    ax.set_xlabel("Block width w")
    ax.set_ylabel("Throughput (Mbit/s)")
    ax.grid(True, alpha=0.22, linewidth=0.5)
    ax.set_xticks(widths[:: max(1, len(widths) // 7)])
    twin = ax.twinx()
    # Use the continuous monotone compute trend for the right-axis guide while
    # retaining raw ceiling-based operation counts in the CSV.
    ops = [float(row.get("theoretical_continuous_ops", row["theoretical_ops"])) for row in rows]
    twin.plot(widths, ops, color="#2ca02c", linewidth=1.2, alpha=0.75, marker="s", markersize=3, label="compute trend")
    if show_right_label:
        twin.set_ylabel("Compute model (monotone trend)")
    else:
        twin.tick_params(right=False, labelright=False)


def plot_fig3(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    _setup_style()
    panels = load_panel_rows(csv_path)
    if not panels:
        raise ValueError(f"no timed Round 31 Fig. 3 rows in {csv_path}")
    profiles = [profile for profile in PROFILE_TITLES if profile in panels] or sorted(panels)
    cols = 2
    rows_count = (len(profiles) + cols - 1) // cols
    fig, axes = plt.subplots(rows_count, cols, figsize=(7.8, 3.35 * rows_count), squeeze=False)
    for idx, profile in enumerate(profiles):
        ax = axes[idx // cols][idx % cols]
        _plot_panel(ax, profile, panels[profile], show_right_label=(idx % cols == cols - 1))
    for idx in range(len(profiles), rows_count * cols):
        axes[idx // cols][idx % cols].axis("off")
    cache_handles = [
        plt.Rectangle((0, 0), 1, 1, color=color, alpha=0.48, label=level) for level, color in CACHE_COLORS.items()
    ]
    fig.legend(
        cache_handles,
        [h.get_label() for h in cache_handles],
        loc="lower center",
        bbox_to_anchor=(0.5, 0.01),
        ncol=4,
        frameon=True,
    )
    fig.subplots_adjust(top=0.95, bottom=0.12, hspace=0.48, wspace=0.32)
    _save(fig, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round 31 Fig. 3 cache-width sweep.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig3(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
