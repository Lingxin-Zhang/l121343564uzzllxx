"""Plot Round34 Fig3: multi-code three-backend syndrome throughput bars.

Inputs:
  - results/raw/round34_multicode_three_backend_syndrome_summary.csv
    Required columns include profile, backend, batch_size,
    is_representative_batch, throughput_Mbit_s, and cv.
Outputs:
  - results/figures/round34_fig3_multicode_three_backend.{png,pdf}
  - results/raw/round34_fig3_multicode_representative.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "results" / "raw" / "round34_multicode_three_backend_syndrome_summary.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
DEFAULT_REPRESENTATIVE_OUTPUT = ROOT / "results" / "raw" / "round34_fig3_multicode_representative.csv"
OUTPUT_STEM = "round34_fig3_multicode_three_backend"

COLORS = {
    "naive": "#A9C7E0",
    "direct": "#7E9BB8",
    "lut": "#D9825B",
}

BACKENDS = [
    ("galois_per_codeword", "naive per-codeword", COLORS["naive"]),
    ("PackedBatchGF2Kernel.apply_many", "direct vectorized GF(2) matmul", COLORS["direct"]),
    ("PackedBlockLUTKernel.apply_many_packed", "block-LUT (cache-aware)", COLORS["lut"]),
]

PROFILE_LABELS = {
    "bch_255_239_r16": "BCH(255,239)\nr=16",
    "bch_255_231_r24": "BCH(255,231)\nr=24",
    "bch_511_484_r27": "BCH(511,484)\nr=27",
    "bch_1023_993_r30": "BCH(1023,993)\nr=30",
}

PROFILE_ORDER = list(PROFILE_LABELS)


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def load_representative_rows(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    required = {
        "profile",
        "task",
        "backend",
        "batch_size",
        "is_representative_batch",
        "throughput_Mbit_s",
        "cv",
        "correctness_passed",
        "timed",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"missing required columns in {csv_path}: {missing}")
    mask = (
        (df["task"] == "syndrome")
        & _as_bool(df["is_representative_batch"])
        & _as_bool(df["correctness_passed"])
        & _as_bool(df["timed"])
    )
    rep = df.loc[mask].copy()
    expected = {(profile, backend) for profile in PROFILE_ORDER for backend, _, _ in BACKENDS}
    found = {(row.profile, row.backend) for row in rep.itertuples()}
    missing_pairs = sorted(expected - found)
    if missing_pairs:
        raise ValueError(f"representative rows missing profile/backend pairs: {missing_pairs}")
    rep["profile"] = pd.Categorical(rep["profile"], PROFILE_ORDER, ordered=True)
    rep["backend"] = pd.Categorical(rep["backend"], [backend for backend, _, _ in BACKENDS], ordered=True)
    rep = rep.sort_values(["profile", "backend"]).reset_index(drop=True)
    return rep


def write_representative_csv(rep: pd.DataFrame, output: Path) -> pd.DataFrame:
    rows = []
    for profile in PROFILE_ORDER:
        subset = rep[rep["profile"].astype(str) == profile]
        direct = float(subset[subset["backend"].astype(str) == "PackedBatchGF2Kernel.apply_many"]["throughput_Mbit_s"].iloc[0])
        naive = float(subset[subset["backend"].astype(str) == "galois_per_codeword"]["throughput_Mbit_s"].iloc[0])
        lut = float(
            subset[subset["backend"].astype(str) == "PackedBlockLUTKernel.apply_many_packed"]["throughput_Mbit_s"].iloc[0]
        )
        for row in subset.to_dict("records"):
            copied = dict(row)
            copied["lut_vs_direct"] = lut / direct if direct > 0 else np.nan
            copied["lut_vs_naive"] = lut / naive if naive > 0 else np.nan
            rows.append(copied)
    out = pd.DataFrame(rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    return out


def plot(rep: pd.DataFrame, output_dir: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.labelsize": 11,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "axes.unicode_minus": False,
        }
    )
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    x = np.arange(len(PROFILE_ORDER), dtype=float)
    width = 0.24
    offsets = np.array([-width, 0.0, width])
    max_value = 0.0
    for idx, (backend, label, color) in enumerate(BACKENDS):
        values = []
        for profile in PROFILE_ORDER:
            row = rep[(rep["profile"].astype(str) == profile) & (rep["backend"].astype(str) == backend)]
            value = float(row["throughput_Mbit_s"].iloc[0])
            values.append(value)
            max_value = max(max_value, value)
        ax.bar(
            x + offsets[idx],
            values,
            width=width,
            label=label,
            color=color,
            edgecolor="white",
            linewidth=0.8,
            zorder=3,
        )

    for pos, profile in zip(x, PROFILE_ORDER, strict=True):
        subset = rep[rep["profile"].astype(str) == profile]
        lut = float(subset[subset["backend"].astype(str) == "PackedBlockLUTKernel.apply_many_packed"]["throughput_Mbit_s"].iloc[0])
        direct = float(subset[subset["backend"].astype(str) == "PackedBatchGF2Kernel.apply_many"]["throughput_Mbit_s"].iloc[0])
        ratio = lut / direct if direct > 0 else np.nan
        ax.text(
            pos + width,
            lut * 1.16,
            f"{ratio:.1f}x",
            ha="center",
            va="bottom",
            color=COLORS["lut"],
            fontweight="bold",
            fontsize=9,
            zorder=5,
        )

    ax.set_yscale("log")
    ax.set_ylabel("Syndrome throughput (Mbit/s)")
    ax.set_xticks(x)
    ax.set_xticklabels([PROFILE_LABELS[p] for p in PROFILE_ORDER])
    ax.set_ylim(bottom=max(0.5, min(rep["throughput_Mbit_s"]) * 0.55), top=max_value * 3.0)
    ax.grid(axis="y", linestyle=":", alpha=0.45, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=3,
        frameon=False,
        borderaxespad=0.0,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.png", dpi=300)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.pdf")
    plt.close(fig)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round34 multi-code throughput bar figure.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--representative-output", type=Path, default=DEFAULT_REPRESENTATIVE_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    rep = load_representative_rows(args.csv)
    write_representative_csv(rep, args.representative_output)
    plot(rep, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
