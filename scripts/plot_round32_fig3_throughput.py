"""Plot Round 32 Fig. 3 throughput-vs-batch views."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "results" / "raw" / "round32_fig3_throughput_rounds.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
PROFILE = "bch_255_239_r16"
OUTPUT_STEM = "round32_fig3_throughput"

DISPLAY_BACKEND = {
    "PackedBatchGF2Kernel.apply_many": "direct vectorized GF(2) matmul",
    "PackedBlockLUTKernel.apply_many_packed": "block-LUT (cache-aware)",
    "galois_per_codeword": "naive per-codeword",
}


def _value_column(df: pd.DataFrame) -> str:
    if "throughput_norm_Mbit_s" in df.columns and df["throughput_norm_Mbit_s"].notna().any():
        return "throughput_norm_Mbit_s"
    return "throughput_Mbit_s"


def aggregate_rounds(csv_path: Path = DEFAULT_CSV) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    df = df[df["profile"].eq(PROFILE)]
    value_col = _value_column(df)
    group_cols = ["profile", "task", "backend", "batch_size"]
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
    agg["throughput_cv"] = agg["throughput_std_Mbit_s"] / agg["throughput_median_Mbit_s"]
    return agg


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _plot_summary(agg: pd.DataFrame, output_dir: Path, *, metric: str, stem: str, title_suffix: str) -> None:
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
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=False)
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome", "(b) Parity")):
        ax.axvspan(100, 10_000, color="#D9EAF7", alpha=0.28)
        sub = agg[agg["task"].eq(task)]
        for backend, label in DISPLAY_BACKEND.items():
            rows = sub[sub["backend"].eq(backend)].sort_values("batch_size")
            if rows.empty:
                continue
            ax.plot(
                rows["batch_size"],
                rows[metric],
                marker="o" if backend != "galois_per_codeword" else "x",
                linestyle=styles[backend],
                color=colors[backend],
                linewidth=1.8 if backend == "PackedBlockLUTKernel.apply_many_packed" else 1.2,
                alpha=0.95 if backend != "galois_per_codeword" else 0.5,
                label=label,
            )
            if metric == "throughput_median_Mbit_s" and backend == "PackedBlockLUTKernel.apply_many_packed":
                lower = rows[metric] - rows["throughput_min_Mbit_s"]
                upper = rows["throughput_max_Mbit_s"] - rows[metric]
                ax.errorbar(rows["batch_size"], rows[metric], yerr=[lower, upper], fmt="none", ecolor="#666666", capsize=2)
        ax.set_xscale("log")
        ax.set_title(f"{title} {title_suffix}")
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, which="both", alpha=0.24)
    handles, labels = axes[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=3, frameon=True)
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.25)
    _save(fig, output_dir, stem)


def _plot_scatter(csv_path: Path, output_dir: Path) -> None:
    df = pd.read_csv(csv_path)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    df = df[df["profile"].eq(PROFILE)]
    value_col = _value_column(df)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=False)
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome", "(b) Parity")):
        sub = df[df["task"].eq(task)]
        for backend, label in DISPLAY_BACKEND.items():
            rows = sub[sub["backend"].eq(backend)]
            if rows.empty:
                continue
            ax.scatter(rows["batch_size"], rows[value_col], s=16, alpha=0.55, label=label)
        ax.set_xscale("log")
        ax.set_title(f"{title} all rounds")
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, which="both", alpha=0.24)
    handles, labels = axes[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=3, frameon=True)
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.25)
    _save(fig, output_dir, f"{OUTPUT_STEM}_scatter")


def plot_fig3(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    agg = aggregate_rounds(csv_path)
    _plot_summary(agg, output_dir, metric="throughput_median_Mbit_s", stem=OUTPUT_STEM, title_suffix="median")
    _plot_summary(agg, output_dir, metric="throughput_min_Mbit_s", stem=f"{OUTPUT_STEM}_min", title_suffix="min")
    _plot_summary(agg, output_dir, metric="throughput_max_Mbit_s", stem=f"{OUTPUT_STEM}_envelope", title_suffix="max envelope")
    _plot_scatter(csv_path, output_dir)
    return agg


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round32 Fig3 throughput views.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--summary-csv", type=Path, default=ROOT / "results" / "raw" / "round32_fig3_throughput_summary.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    agg = plot_fig3(args.csv, args.output_dir)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.summary_csv, index=False)
    print(f"wrote {args.summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
