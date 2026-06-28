"""Plot and summarize Round33 dense-batch Fig. 3 data."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_THROUGHPUT = ROOT / "results" / "raw" / "round33_fig3_throughput_all.csv"
DEFAULT_STAGES = ROOT / "results" / "raw" / "round33_fig3_stage_breakdown_all.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
DEFAULT_SUMMARY = ROOT / "results" / "raw" / "round33_fig3_throughput_summary.csv"
DEFAULT_SPEEDUPS = ROOT / "results" / "raw" / "round33_fig3_speedup_summary.csv"
OUTPUT_STEM = "round33_fig3_dense_batch"
PROFILE = "bch_255_239_r16"
BACKEND_DIRECT = "PackedBatchGF2Kernel.apply_many"
BACKEND_LUT = "PackedBlockLUTKernel.apply_many_packed"
DISPLAY = {BACKEND_DIRECT: "direct vectorized GF(2) matmul", BACKEND_LUT: "block-LUT (w=14)"}


def _filtered(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    if "profile" in df.columns:
        df = df[df["profile"].eq(PROFILE)]
    return df


def aggregate_throughput(path: Path = DEFAULT_THROUGHPUT) -> pd.DataFrame:
    df = _filtered(path)
    group_cols = ["profile", "task", "mode", "backend", "batch_size"]
    agg = (
        df.groupby(group_cols, as_index=False)["throughput_Mbit_s"]
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


def summarize_speedups(path: Path = DEFAULT_THROUGHPUT) -> pd.DataFrame:
    agg = aggregate_throughput(path)
    rows = []
    for (task, mode, batch), group in agg.groupby(["task", "mode", "batch_size"]):
        direct = group[group["backend"].eq(BACKEND_DIRECT)]
        lut = group[group["backend"].eq(BACKEND_LUT)]
        if direct.empty or lut.empty:
            continue
        rows.append(
            {
                "task": task,
                "mode": mode,
                "batch_size": int(batch),
                "direct_median_Mbit_s": float(direct.iloc[0]["throughput_median_Mbit_s"]),
                "lut_median_Mbit_s": float(lut.iloc[0]["throughput_median_Mbit_s"]),
                "lut_vs_direct_median": float(lut.iloc[0]["throughput_median_Mbit_s"] / direct.iloc[0]["throughput_median_Mbit_s"]),
                "direct_min_Mbit_s": float(direct.iloc[0]["throughput_min_Mbit_s"]),
                "lut_min_Mbit_s": float(lut.iloc[0]["throughput_min_Mbit_s"]),
                "lut_vs_direct_min": float(lut.iloc[0]["throughput_min_Mbit_s"] / direct.iloc[0]["throughput_min_Mbit_s"]),
                "direct_cv": float(direct.iloc[0]["throughput_cv"]),
                "lut_cv": float(lut.iloc[0]["throughput_cv"]),
            }
        )
    return pd.DataFrame(rows)


def _save(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _plot_metric(agg: pd.DataFrame, output_dir: Path, *, metric: str, stem: str, title_suffix: str, errorbars: bool) -> None:
    data = agg[agg["mode"].eq("bulk")]
    colors = {BACKEND_DIRECT: "#555555", BACKEND_LUT: "#2AA6A1"}
    styles = {BACKEND_DIRECT: "--", BACKEND_LUT: "-"}
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=False)
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome", "(b) Parity")):
        ax.axvspan(300, 3_000, color="#D9EAF7", alpha=0.28)
        sub = data[data["task"].eq(task)]
        for backend in (BACKEND_DIRECT, BACKEND_LUT):
            rows = sub[sub["backend"].eq(backend)].sort_values("batch_size")
            if rows.empty:
                continue
            ax.plot(rows["batch_size"], rows[metric], marker="o", color=colors[backend], linestyle=styles[backend], linewidth=1.7, label=DISPLAY[backend])
            if errorbars and backend == BACKEND_LUT:
                lower = rows[metric] - rows["throughput_min_Mbit_s"]
                upper = rows["throughput_max_Mbit_s"] - rows[metric]
                ax.errorbar(rows["batch_size"], rows[metric], yerr=[lower, upper], fmt="none", ecolor="#666666", capsize=2, linewidth=0.7)
        ax.set_xscale("log")
        ax.set_title(f"{title} {title_suffix}")
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, which="both", alpha=0.24)
    handles, labels = axes[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=2, frameon=True)
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.25)
    _save(fig, output_dir, stem)


def _plot_scatter(path: Path, output_dir: Path) -> None:
    df = _filtered(path)
    df = df[df["mode"].eq("bulk")]
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=False)
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome", "(b) Parity")):
        sub = df[df["task"].eq(task)]
        if sub.empty:
            ax.text(0.5, 0.5, "No timed data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            continue
        for backend, color in ((BACKEND_DIRECT, "#555555"), (BACKEND_LUT, "#2AA6A1")):
            rows = sub[sub["backend"].eq(backend)]
            ax.scatter(rows["batch_size"], rows["throughput_Mbit_s"], s=14, alpha=0.5, color=color, label=DISPLAY[backend])
        ax.set_xscale("log")
        ax.set_title(f"{title} all rounds")
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, which="both", alpha=0.24)
    handles, labels = axes[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    fig.legend(unique.values(), unique.keys(), loc="upper center", ncol=2, frameon=True)
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.25)
    _save(fig, output_dir, "round33_fig3_scatter")


def _plot_stage(stage_path: Path, output_dir: Path) -> None:
    df = pd.read_csv(stage_path)
    if "profile" in df.columns:
        df = df[df["profile"].eq(PROFILE)]
    stage_cols = [
        "stage_read_prepare_pct",
        "stage_index_pct",
        "stage_lookup_pct",
        "stage_xor_pct",
        "stage_write_pct",
    ]
    labels = ["read/prepare", "index", "lookup", "xor", "write"]
    fig, axes = plt.subplots(1, 2, figsize=(7.8, 3.0), sharey=True)
    for ax, task, title in zip(axes, ("syndrome", "parity"), ("(a) Syndrome stages", "(b) Parity stages")):
        sub = df[df["task"].eq(task)]
        if sub.empty:
            ax.axis("off")
            continue
        grouped = sub.groupby("batch_size", as_index=False)[stage_cols].median().sort_values("batch_size")
        ax.stackplot(grouped["batch_size"], [grouped[col] for col in stage_cols], labels=labels, alpha=0.88)
        ax.set_xscale("log")
        ax.set_ylim(0, 100)
        ax.set_title(title)
        ax.set_xlabel("Batch size (codewords)")
        ax.set_ylabel("Stage share (%)")
        ax.grid(True, which="both", alpha=0.2)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, frameon=True)
    fig.subplots_adjust(top=0.78, bottom=0.18, wspace=0.22)
    _save(fig, output_dir, "round33_fig3_stage_breakdown")


def plot_all(
    throughput_csv: Path = DEFAULT_THROUGHPUT,
    stage_csv: Path = DEFAULT_STAGES,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    agg = aggregate_throughput(throughput_csv)
    _plot_metric(agg, output_dir, metric="throughput_min_Mbit_s", stem=OUTPUT_STEM, title_suffix="min view", errorbars=True)
    _plot_metric(agg, output_dir, metric="throughput_median_Mbit_s", stem=f"{OUTPUT_STEM}_median", title_suffix="median", errorbars=True)
    _plot_metric(agg, output_dir, metric="throughput_max_Mbit_s", stem=f"{OUTPUT_STEM}_envelope", title_suffix="max envelope", errorbars=False)
    _plot_scatter(throughput_csv, output_dir)
    _plot_stage(stage_csv, output_dir)
    return agg, summarize_speedups(throughput_csv)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round33 Fig3 dense-batch artifacts.")
    parser.add_argument("--throughput-csv", type=Path, default=DEFAULT_THROUGHPUT)
    parser.add_argument("--stage-csv", type=Path, default=DEFAULT_STAGES)
    parser.add_argument("--summary-csv", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--speedup-csv", type=Path, default=DEFAULT_SPEEDUPS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    agg, speedups = plot_all(args.throughput_csv, args.stage_csv, args.output_dir)
    args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.summary_csv, index=False)
    speedups.to_csv(args.speedup_csv, index=False)
    print(f"wrote {args.summary_csv}")
    print(f"wrote {args.speedup_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
