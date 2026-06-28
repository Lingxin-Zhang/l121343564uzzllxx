"""Plot Round34 Fig3(b): real OFEC end-to-end decode time comparison.

Inputs:
  - results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv
  - results/raw/round31_fig4_real_ofec_block_lut_ber.csv
The plotted values are the sums of decode_sec across the shared SNR points.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
DEFAULT_REFERENCE_CSV = RAW_DIR / "round31_fig4_real_ofec_syndrome_lut_ber.csv"
DEFAULT_BLOCK_LUT_CSV = RAW_DIR / "round31_fig4_real_ofec_block_lut_ber.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
DEFAULT_SUMMARY_OUTPUT = RAW_DIR / "round34_fig3b_decode_time_summary.csv"
OUTPUT_STEM = "round34_fig3b_decode_time"

C_REFERENCE = "#7E9BB8"
C_LUT = "#D9825B"


def build_decode_summary(reference_csv: Path, block_lut_csv: Path) -> pd.DataFrame:
    ref = pd.read_csv(reference_csv)
    lut = pd.read_csv(block_lut_csv)
    required = {"snr_db", "decode_sec", "elapsed_sec", "backend"}
    for path, df in ((reference_csv, ref), (block_lut_csv, lut)):
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"missing required columns in {path}: {missing}")
    shared = set(ref["snr_db"]).intersection(set(lut["snr_db"]))
    if len(shared) != len(ref) or len(shared) != len(lut):
        raise ValueError("decode-time curves do not have identical SNR points")
    rows = [
        {
            "backend": "reference syndrome backend",
            "source_csv": str(reference_csv),
            "snr_points": len(ref),
            "snr_min": float(ref["snr_db"].min()),
            "snr_max": float(ref["snr_db"].max()),
            "total_decode_sec": float(ref["decode_sec"].sum()),
            "total_elapsed_sec": float(ref["elapsed_sec"].sum()),
        },
        {
            "backend": "block-LUT backend",
            "source_csv": str(block_lut_csv),
            "snr_points": len(lut),
            "snr_min": float(lut["snr_db"].min()),
            "snr_max": float(lut["snr_db"].max()),
            "total_decode_sec": float(lut["decode_sec"].sum()),
            "total_elapsed_sec": float(lut["elapsed_sec"].sum()),
        },
    ]
    summary = pd.DataFrame(rows)
    reference_time = float(summary.loc[summary["backend"] == "reference syndrome backend", "total_decode_sec"].iloc[0])
    lut_time = float(summary.loc[summary["backend"] == "block-LUT backend", "total_decode_sec"].iloc[0])
    summary["reference_decode_over_block_lut"] = reference_time / lut_time if lut_time > 0 else float("nan")
    return summary


def plot(summary: pd.DataFrame, output_dir: Path) -> None:
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
    labels = ["reference\nbackend", "block-LUT\nbackend"]
    values = summary["total_decode_sec"].to_numpy(dtype=float)
    colors = [C_REFERENCE, C_LUT]
    fig, ax = plt.subplots(figsize=(4.2, 3.7))
    ax.bar([0, 1], values, width=0.58, color=colors, edgecolor="white", linewidth=0.8, zorder=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(labels)
    ax.set_ylabel("Total decode time (s)")
    ax.grid(axis="y", linestyle=":", alpha=0.45, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_ylim(0, max(values) * 1.18)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.png", dpi=300)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.pdf")
    plt.close(fig)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round34 real OFEC decode-time comparison.")
    parser.add_argument("--reference-csv", type=Path, default=DEFAULT_REFERENCE_CSV)
    parser.add_argument("--block-lut-csv", type=Path, default=DEFAULT_BLOCK_LUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summary = build_decode_summary(args.reference_csv, args.block_lut_csv)
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.summary_output, index=False)
    plot(summary, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
