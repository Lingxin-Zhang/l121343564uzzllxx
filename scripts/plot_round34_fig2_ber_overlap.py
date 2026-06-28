"""Plot Round34 Fig2: real OFEC BER overlap for reference and block-LUT backends.

Inputs:
  - results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv
  - results/raw/round31_fig4_real_ofec_block_lut_ber.csv
  - results/raw/round31_fig4_real_ofec_curve_diff.csv
The plotted values are read directly from the BER CSV files; the diff CSV is
used as a gate that the paired post-FEC BER deltas are zero.
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
DEFAULT_DIFF_CSV = RAW_DIR / "round31_fig4_real_ofec_curve_diff.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round34_fig2_real_ofec_ber_overlap"

C_REFERENCE = "#A9C7E0"
C_LUT = "#D9825B"


def _load_curves(reference_csv: Path, block_lut_csv: Path, diff_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref = pd.read_csv(reference_csv).sort_values("snr_db")
    lut = pd.read_csv(block_lut_csv).sort_values("snr_db")
    required = {"snr_db", "post_fec_ber"}
    for path, df in ((reference_csv, ref), (block_lut_csv, lut)):
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"missing required columns in {path}: {missing}")
    merged = ref[["snr_db", "post_fec_ber"]].merge(
        lut[["snr_db", "post_fec_ber"]], on="snr_db", suffixes=("_reference", "_block_lut")
    )
    if len(merged) != len(ref) or len(merged) != len(lut):
        raise ValueError("reference and block-LUT curves do not have identical SNR points")
    if (merged[["post_fec_ber_reference", "post_fec_ber_block_lut"]] <= 0).any().any():
        raise ValueError("Post-FEC BER must be positive for a log-scale BER plot")
    if diff_csv.exists():
        diff = pd.read_csv(diff_csv)
        if "matched" in diff.columns and not diff["matched"].astype(str).str.lower().isin({"true", "1"}).all():
            raise ValueError(f"non-matching rows found in {diff_csv}")
        for col in ("post_fec_errors_delta", "post_fec_ber_delta"):
            if col in diff.columns and (diff[col].abs() > 0).any():
                raise ValueError(f"non-zero {col} found in {diff_csv}")
    return ref, lut


def plot(reference: pd.DataFrame, block_lut: pd.DataFrame, output_dir: Path) -> None:
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
    fig, ax = plt.subplots(figsize=(5.7, 3.8))
    ax.semilogy(
        reference["snr_db"],
        reference["post_fec_ber"],
        color=C_REFERENCE,
        lw=6.0,
        marker="s",
        markersize=13,
        markerfacecolor=C_REFERENCE,
        markeredgecolor="white",
        markeredgewidth=0.9,
        solid_capstyle="round",
        label="reference syndrome backend",
        zorder=2,
    )
    ax.semilogy(
        block_lut["snr_db"],
        block_lut["post_fec_ber"],
        color=C_LUT,
        lw=1.7,
        linestyle=(0, (4, 2)),
        marker="o",
        markersize=4.8,
        markerfacecolor="white",
        markeredgecolor=C_LUT,
        markeredgewidth=1.7,
        label="block-LUT backend",
        zorder=4,
    )
    ax.set_xlabel("SNR (dB)")
    ax.set_ylabel("Post-FEC BER")
    ax.grid(axis="both", linestyle=":", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, borderaxespad=0.0)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.90))
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.png", dpi=300)
    fig.savefig(output_dir / f"{OUTPUT_STEM}.pdf")
    plt.close(fig)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round34 real OFEC BER overlap figure.")
    parser.add_argument("--reference-csv", type=Path, default=DEFAULT_REFERENCE_CSV)
    parser.add_argument("--block-lut-csv", type=Path, default=DEFAULT_BLOCK_LUT_CSV)
    parser.add_argument("--diff-csv", type=Path, default=DEFAULT_DIFF_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    reference, block_lut = _load_curves(args.reference_csv, args.block_lut_csv, args.diff_csv)
    plot(reference, block_lut, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
