"""Plot Round 32 Fig. 4 cache-width views."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WIDTH_CSV = ROOT / "results" / "raw" / "round32_width_throughput_rounds.csv"
DEFAULT_PROBE_CSV = ROOT / "results" / "raw" / "round32_cache_counter_probe.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round32_fig4_cache_width"
CACHE_COLORS = {"L1": "#E8F5E9", "L2": "#E3F2FD", "L3": "#FFF3E0", "DRAM": "#FCE4EC"}
ORDINAL_LABELS = {1: "L1", 2: "L2", 3: "L3", 4: "DRAM"}
PROFILE_TITLES = {
    "bch_255_239_r16": "BCH(255,239), r=16",
    "bch_255_231_r24": "BCH(255,231), r=24",
    "bch_511_484_r27": "BCH(511,484), r=27",
    "bch_1023_993_r30": "BCH(1023,993), r=30",
}


def aggregate_width_rounds(width_csv: Path = DEFAULT_WIDTH_CSV) -> pd.DataFrame:
    df = pd.read_csv(width_csv)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    value_col = "throughput_norm_Mbit_s" if "throughput_norm_Mbit_s" in df.columns and df["throughput_norm_Mbit_s"].notna().any() else "throughput_Mbit_s"
    group_cols = ["profile", "task", "block_width"]
    passthrough = ["cache_level_fit", "theoretical_ops"]
    agg = (
        df.groupby(group_cols, as_index=False)[value_col]
        .agg(["median", "min", "max", "std", "count"])
        .reset_index()
        .rename(
            columns={
                "median": "throughput_median_Mbit_s",
                "min": "throughput_min_Mbit_s",
                "max": "throughput_max_Mbit_s",
                "std": "throughput_std_Mbit_s",
                "count": "round_count",
            }
        )
    )
    first = df.groupby(group_cols, as_index=False)[passthrough].first()
    agg = agg.merge(first, on=group_cols, how="left")
    agg["throughput_cv"] = agg["throughput_std_Mbit_s"] / agg["throughput_median_Mbit_s"]
    return agg


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _background_cache_bands(ax: plt.Axes, rows: pd.DataFrame) -> None:
    widths = rows["block_width"].astype(int).tolist()
    if not widths:
        return
    edges = [widths[0] - 0.5]
    edges.extend((a + b) / 2 for a, b in zip(widths, widths[1:]))
    edges.append(widths[-1] + 0.5)
    for idx, (_, row) in enumerate(rows.iterrows()):
        ax.axvspan(edges[idx], edges[idx + 1], color=CACHE_COLORS.get(row["cache_level_fit"], "#EEEEEE"), alpha=0.35)


def _plot_main(
    agg: pd.DataFrame,
    probe: pd.DataFrame,
    output_dir: Path,
    stem: str,
    *,
    profiles: list[str],
    metric: str = "throughput_median_Mbit_s",
    title_suffix: str = "median",
) -> None:
    rows_count = len(profiles)
    fig, axes = plt.subplots(rows_count, 2, figsize=(7.6, max(3.1, 2.7 * rows_count)), squeeze=False)
    for ridx, profile in enumerate(profiles):
        left = axes[ridx][0]
        right = axes[ridx][1]
        rows = agg[(agg["profile"].eq(profile)) & (agg["task"].eq("syndrome"))].sort_values("block_width")
        if rows.empty:
            left.axis("off")
        else:
            _background_cache_bands(left, rows)
            if metric == "throughput_median_Mbit_s":
                left.errorbar(
                    rows["block_width"],
                    rows[metric],
                    yerr=[
                        rows[metric] - rows["throughput_min_Mbit_s"],
                        rows["throughput_max_Mbit_s"] - rows[metric],
                    ],
                    marker="o",
                    color="#2AA6A1",
                    ecolor="#666666",
                    capsize=2,
                    linewidth=1.5,
                    label="median throughput",
                )
            else:
                left.plot(rows["block_width"], rows[metric], marker="o", color="#2AA6A1", linewidth=1.5)
            best = rows.loc[rows[metric].idxmax()]
            left.scatter([best["block_width"]], [best[metric]], color="#8B1A1A", zorder=4)
            twin = left.twinx()
            twin.plot(rows["block_width"], rows["theoretical_ops"], color="#2ca02c", marker="s", markersize=3, linewidth=1.1)
            twin.tick_params(axis="y", labelsize=7, pad=1)
            left.set_title(f"{PROFILE_TITLES.get(profile, profile)}: {title_suffix}")
            left.set_xlabel("Block width w")
            left.set_ylabel("Throughput (Mbit/s)")
            left.grid(True, alpha=0.24)
        probe_rows = probe[probe["profile"].eq(profile)].sort_values(["batch_size", "block_width"])
        if probe_rows.empty:
            right.axis("off")
        else:
            for batch, group in probe_rows.groupby("batch_size"):
                right.step(group["block_width"], group["cache_level_ordinal"], where="mid", marker="o", label=f"batch={batch}")
            right.set_yticks([1, 2, 3, 4], [ORDINAL_LABELS[i] for i in [1, 2, 3, 4]])
            mode = str(probe_rows["counter_mode"].iloc[0])
            right.set_title(f"{PROFILE_TITLES.get(profile, profile)}: {mode}")
            right.set_xlabel("Block width w")
            right.set_ylabel("Counter/fallback level")
            right.grid(True, alpha=0.24)
            right.legend(fontsize=7, frameon=True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c, alpha=0.35, label=k) for k, c in CACHE_COLORS.items()]
    fig.legend(handles, [h.get_label() for h in handles], loc="lower center", ncol=4, frameon=True)
    fig.subplots_adjust(bottom=0.15, hspace=0.46, wspace=0.48)
    _save(fig, output_dir, stem)


def _plot_scatter(width_csv: Path, output_dir: Path) -> None:
    df = pd.read_csv(width_csv)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    profiles = [p for p in PROFILE_TITLES if p in set(df["profile"])]
    if not profiles:
        profiles = sorted(df["profile"].unique())
    profiles = profiles[:4]
    fig, axes = plt.subplots(len(profiles), 1, figsize=(6.8, max(2.6, 2.25 * len(profiles))), squeeze=False)
    value_col = "throughput_norm_Mbit_s" if "throughput_norm_Mbit_s" in df.columns and df["throughput_norm_Mbit_s"].notna().any() else "throughput_Mbit_s"
    for idx, profile in enumerate(profiles):
        ax = axes[idx][0]
        rows = df[(df["profile"].eq(profile)) & (df["task"].eq("syndrome"))]
        if rows.empty:
            ax.axis("off")
            continue
        for round_index, group in rows.groupby("round_index"):
            ax.scatter(group["block_width"], group[value_col], s=14, alpha=0.45, label=f"round {round_index}")
        ordered = rows.sort_values("block_width").drop_duplicates("block_width")
        twin = ax.twinx()
        twin.plot(ordered["block_width"], ordered["theoretical_ops"], color="#2ca02c", linewidth=1.0, alpha=0.8)
        twin.tick_params(axis="y", labelsize=7, pad=1)
        ax.set_title(f"{PROFILE_TITLES.get(profile, profile)}: all rounds")
        ax.set_xlabel("Block width w")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, alpha=0.24)
    fig.subplots_adjust(hspace=0.55)
    _save(fig, output_dir, f"{OUTPUT_STEM}_scatter")


def plot_fig4(
    width_csv: Path = DEFAULT_WIDTH_CSV,
    probe_csv: Path = DEFAULT_PROBE_CSV,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> pd.DataFrame:
    agg = aggregate_width_rounds(width_csv)
    probe = pd.read_csv(probe_csv)
    profiles = [p for p in ("bch_255_239_r16", "bch_255_231_r24", "bch_511_484_r27", "bch_1023_993_r30") if p in set(agg["profile"])]
    if not profiles:
        profiles = sorted(agg["profile"].unique())
    _plot_main(agg, probe, output_dir, OUTPUT_STEM, profiles=profiles[:4])
    _plot_main(agg, probe, output_dir, f"{OUTPUT_STEM}_min", profiles=profiles[:4], metric="throughput_min_Mbit_s", title_suffix="min")
    _plot_main(agg, probe, output_dir, f"{OUTPUT_STEM}_envelope", profiles=profiles[:4], metric="throughput_max_Mbit_s", title_suffix="max envelope")
    _plot_main(agg, probe, output_dir, f"{OUTPUT_STEM}_selected_r16_r24", profiles=profiles[:2])
    _plot_scatter(width_csv, output_dir)
    return agg


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round32 Fig4 cache-width views.")
    parser.add_argument("--width-csv", type=Path, default=DEFAULT_WIDTH_CSV)
    parser.add_argument("--probe-csv", type=Path, default=DEFAULT_PROBE_CSV)
    parser.add_argument("--summary-csv", type=Path, default=ROOT / "results" / "raw" / "round32_width_throughput_summary.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    agg = plot_fig4(args.width_csv, args.probe_csv, args.output_dir)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.summary_csv, index=False)
    print(f"wrote {args.summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
