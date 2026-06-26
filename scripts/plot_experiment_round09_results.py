"""Plot long-stream cache-width diagnostics for experiment round 09."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
SUMMARY_DIR = ROOT / "results" / "summary"
FIGURE_DIR = ROOT / "results" / "figures"
FIGURE_NAME = "experiment_round09_long_stream_cache_width"

CACHE_COLORS = {
    "L1": "#0072B2",
    "L2": "#009E73",
    "L3": "#D55E00",
    "memory": "#CC79A7",
}


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(row: dict[str, Any], key: str) -> float:
    return float(row.get(key, "nan"))


def _truthy(row: dict[str, Any], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() in {"true", "1", "yes"}


def plot_long_stream_cache_width(
    *,
    raw_path: Path = RAW_DIR / "long_stream_cache_width.csv",
    summary_path: Path = SUMMARY_DIR / "long_stream_cache_width_summary.csv",
    figure_dir: Path = FIGURE_DIR,
) -> None:
    raw_rows = _read_csv(raw_path)
    summary_rows = _read_csv(summary_path)
    if not raw_rows or not summary_rows:
        raise ValueError("long-stream cache-width CSVs are empty")

    max_total_bits = max(int(float(row["total_bits"])) for row in raw_rows)
    selected_raw = [row for row in raw_rows if int(float(row["total_bits"])) == max_total_bits]
    line_groups = sorted(
        {
            (row.get("code_profile", row.get("matrix_source", "")), int(float(row["iterations"])))
            for row in selected_raw
        }
    )

    fig, axes = plt.subplots(1, 2, figsize=(8.2, 3.4))
    ax = axes[0]
    for code_profile, iteration in line_groups:
        rows = [
            row
            for row in selected_raw
            if row.get("code_profile", row.get("matrix_source", "")) == code_profile
            and int(float(row["iterations"])) == iteration
        ]
        ordered = sorted(rows, key=lambda row: int(float(row["block_width"])))
        ax.plot(
            [int(float(row["block_width"])) for row in ordered],
            [_float(row, "latency_per_word_us") for row in ordered],
            marker="o",
            linewidth=1.4,
            markersize=3,
            label=f"{code_profile} | i={iteration}",
        )
        for row in ordered:
            cache_level = row["cache_level"]
            ax.scatter(
                [int(float(row["block_width"]))],
                [_float(row, "latency_per_word_us")],
                color=CACHE_COLORS.get(cache_level, "#333333"),
                s=18,
                zorder=3,
            )
    ax.set_title(f"Long stream latency ({max_total_bits:,} bits)")
    ax.set_xlabel("block_width")
    ax.set_ylabel("latency / word (us)")
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.legend(frameon=False, fontsize=7)

    ax = axes[1]
    ordered_summary = sorted(
        summary_rows,
        key=lambda row: (int(float(row["total_bits"])), int(float(row["iterations"]))),
    )
    labels = [
        (
            f"{row.get('code_profile', row.get('matrix_source', ''))}\n"
            f"{int(float(row['total_bits'])) // 1_000_000}M/i{int(float(row['iterations']))}"
        )
        for row in ordered_summary
    ]
    l2_ratios = [_float(row, "best_l2_over_best_l1") for row in ordered_summary]
    l3_ratios = [_float(row, "best_l3_over_best_l1") for row in ordered_summary]
    x_positions = list(range(len(labels)))
    bar_width = 0.36
    ax.bar(
        [x - bar_width / 2 for x in x_positions],
        l2_ratios,
        width=bar_width,
        color=CACHE_COLORS["L2"],
        alpha=0.78,
        label="best L2 / best L1",
    )
    ax.bar(
        [x + bar_width / 2 for x in x_positions],
        l3_ratios,
        width=bar_width,
        color=CACHE_COLORS["L3"],
        alpha=0.78,
        label="best L3 / best L1",
    )
    ax.axhline(1.0, color="#333333", linewidth=1.0, linestyle="--")
    ax.axhline(0.8, color="#990000", linewidth=1.0, linestyle=":", label="20% faster gate")
    for x, row in zip(x_positions, ordered_summary, strict=True):
        if _truthy(row, "l2_strong_20x_claim"):
            ax.text(
                x - bar_width / 2,
                _float(row, "best_l2_over_best_l1") - 0.035,
                "*",
                ha="center",
                va="top",
                fontsize=11,
                color="#111111",
            )
        if _truthy(row, "l3_strong_20x_claim"):
            ax.text(
                x + bar_width / 2,
                _float(row, "best_l3_over_best_l1") - 0.035,
                "*",
                ha="center",
                va="top",
                fontsize=11,
                color="#111111",
            )
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0.55, max(1.08, max(l2_ratios + l3_ratios) * 1.08))
    ax.set_ylabel("latency ratio vs best L1")
    ax.set_title("L2/L3 claim gate")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(frameon=False, fontsize=7)

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color, label=level, markersize=6)
        for level, color in CACHE_COLORS.items()
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, -0.03),
    )
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    figure_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        output = figure_dir / f"{FIGURE_NAME}.{suffix}"
        fig.savefig(output, dpi=240, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def main() -> None:
    plot_long_stream_cache_width()


if __name__ == "__main__":
    main()
