"""Plot Fig2 BER overlay for the existing h=16 curve and a new h=12 sweep.

Inputs:
  - results/raw/round31_fig4_real_ofec_syndrome_lut_ber.csv
  - results/raw/round31_fig4_real_ofec_block_lut_ber.csv
  - results/raw/round31_fig4_real_ofec_curve_diff.csv
  - results/raw/round35_fig2_h12_same_grid_real_ofec_syndrome_lut_ber.csv
  - results/raw/round35_fig2_h12_same_grid_real_ofec_block_lut_ber.csv
  - results/raw/round35_fig2_h12_same_grid_real_ofec_curve_diff.csv
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"

DEFAULT_H16_REFERENCE_CSV = RAW_DIR / "round31_fig4_real_ofec_syndrome_lut_ber.csv"
DEFAULT_H16_BLOCK_LUT_CSV = RAW_DIR / "round31_fig4_real_ofec_block_lut_ber.csv"
DEFAULT_H16_DIFF_CSV = RAW_DIR / "round31_fig4_real_ofec_curve_diff.csv"

DEFAULT_H12_REFERENCE_CSV = RAW_DIR / "round35_fig2_h12_same_grid_real_ofec_syndrome_lut_ber.csv"
DEFAULT_H12_BLOCK_LUT_CSV = RAW_DIR / "round35_fig2_h12_same_grid_real_ofec_block_lut_ber.csv"
DEFAULT_H12_DIFF_CSV = RAW_DIR / "round35_fig2_h12_same_grid_real_ofec_curve_diff.csv"

OUTPUT_STEM = "round35_fig2_real_ofec_h12_h16_overlay"

COLORS = {
    "h16_reference": "#A9C7E0",
    "h16_lut": "#D9825B",
    "h12_reference": "#7E9BB8",
    "h12_lut": "#B76F54",
}


def _truthy(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1"})


def _display_ber(row: pd.Series) -> tuple[float, bool]:
    post_errors = int(row.get("post_fec_errors", 0))
    total_bits = int(row.get("total_bits", 0))
    ber = float(row["post_fec_ber"])
    if post_errors == 0 and total_bits > 0:
        return 1.0 - math.pow(0.05, 1.0 / total_bits), True
    return ber, False


def _load_pair(reference_csv: Path, block_lut_csv: Path, diff_csv: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref = pd.read_csv(reference_csv).sort_values("snr_db").reset_index(drop=True)
    lut = pd.read_csv(block_lut_csv).sort_values("snr_db").reset_index(drop=True)
    required = {"snr_db", "post_fec_ber", "post_fec_errors", "total_bits"}
    for path, df in ((reference_csv, ref), (block_lut_csv, lut)):
        missing = sorted(required - set(df.columns))
        if missing:
            raise ValueError(f"missing required columns in {path}: {missing}")
    merged = ref[["snr_db"]].merge(lut[["snr_db"]], on="snr_db")
    if len(merged) != len(ref) or len(merged) != len(lut):
        raise ValueError(f"reference and block-LUT SNR grids differ for {reference_csv.name}")
    for df in (ref, lut):
        display = df.apply(_display_ber, axis=1, result_type="expand")
        df["display_ber"] = display[0].astype(float)
        df["zero_error_upper_bound"] = display[1].astype(bool)
        if (df["display_ber"] <= 0).any():
            raise ValueError(f"non-positive displayed BER after zero-error handling for {reference_csv.name}")
    if diff_csv.exists():
        diff = pd.read_csv(diff_csv)
        if "matched" in diff.columns and not _truthy(diff["matched"]).all():
            raise ValueError(f"non-matching rows found in {diff_csv}")
        for col in ("post_fec_errors_delta", "post_fec_ber_delta"):
            if col in diff.columns and (diff[col].astype(float).abs() > 0).any():
                raise ValueError(f"non-zero {col} found in {diff_csv}")
    return ref, lut


def _style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 14,
            "axes.labelsize": 18,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "legend.fontsize": 13,
            "axes.unicode_minus": False,
        }
    )


def _plot_pair(
    ax: plt.Axes,
    reference: pd.DataFrame,
    block_lut: pd.DataFrame,
    *,
    h_value: int,
    reference_color: str,
    lut_color: str,
    zorder_base: int,
) -> None:
    ax.semilogy(
        reference["snr_db"],
        reference["display_ber"],
        color=reference_color,
        lw=5.0,
        marker="s",
        markersize=11,
        markerfacecolor=reference_color,
        markeredgecolor="white",
        markeredgewidth=0.85,
        solid_capstyle="round",
        label=f"h={h_value} bit-parallel GF(2)",
        zorder=zorder_base,
    )
    ax.semilogy(
        block_lut["snr_db"],
        block_lut["display_ber"],
        color=lut_color,
        lw=1.8,
        linestyle=(0, (4, 2)),
        marker="o",
        markersize=5.2,
        markerfacecolor="white",
        markeredgecolor=lut_color,
        markeredgewidth=1.65,
        label=f"h={h_value} block-LUT",
        zorder=zorder_base + 1,
    )
    low_conf = block_lut[block_lut["post_fec_errors"].astype(int) < 10]
    if not low_conf.empty:
        ax.scatter(
            low_conf["snr_db"],
            low_conf["display_ber"],
            facecolors="white",
            edgecolors="#8B1A1A",
            s=80,
            linewidths=1.5,
            zorder=zorder_base + 2,
        )


def plot(
    *,
    h16_reference_csv: Path,
    h16_block_lut_csv: Path,
    h16_diff_csv: Path,
    h12_reference_csv: Path,
    h12_block_lut_csv: Path,
    h12_diff_csv: Path,
    output_dir: Path,
    output_stem: str,
) -> None:
    h16_ref, h16_lut = _load_pair(h16_reference_csv, h16_block_lut_csv, h16_diff_csv)
    h12_ref, h12_lut = _load_pair(h12_reference_csv, h12_block_lut_csv, h12_diff_csv)
    if list(h16_ref["snr_db"].round(10)) != list(h12_ref["snr_db"].round(10)):
        raise ValueError("h=16 and h=12 curves do not use identical SNR grids")

    _style()
    fig, ax = plt.subplots(figsize=(8.6, 5.4))
    _plot_pair(
        ax,
        h16_ref,
        h16_lut,
        h_value=16,
        reference_color=COLORS["h16_reference"],
        lut_color=COLORS["h16_lut"],
        zorder_base=2,
    )
    _plot_pair(
        ax,
        h12_ref,
        h12_lut,
        h_value=12,
        reference_color=COLORS["h12_reference"],
        lut_color=COLORS["h12_lut"],
        zorder_base=5,
    )
    if h16_ref["zero_error_upper_bound"].any() or h12_ref["zero_error_upper_bound"].any():
        ax.text(
            0.03,
            0.05,
            "zero-error points shown as 95% upper bounds",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=11,
            color="#333333",
        )
    ax.set_xlabel("SNR Es/N0 (dB)")
    ax.set_ylabel("Post-FEC BER")
    ax.grid(axis="both", which="both", linestyle=":", alpha=0.45)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=2, frameon=False, borderaxespad=0.0)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.88))
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_dir / f"{output_stem}.png", dpi=300)
    fig.savefig(output_dir / f"{output_stem}.pdf")
    plt.close(fig)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Fig2 h=12/h=16 real OFEC BER overlay.")
    parser.add_argument("--h16-reference-csv", type=Path, default=DEFAULT_H16_REFERENCE_CSV)
    parser.add_argument("--h16-block-lut-csv", type=Path, default=DEFAULT_H16_BLOCK_LUT_CSV)
    parser.add_argument("--h16-diff-csv", type=Path, default=DEFAULT_H16_DIFF_CSV)
    parser.add_argument("--h12-reference-csv", type=Path, default=DEFAULT_H12_REFERENCE_CSV)
    parser.add_argument("--h12-block-lut-csv", type=Path, default=DEFAULT_H12_BLOCK_LUT_CSV)
    parser.add_argument("--h12-diff-csv", type=Path, default=DEFAULT_H12_DIFF_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-stem", default=OUTPUT_STEM)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot(
        h16_reference_csv=args.h16_reference_csv,
        h16_block_lut_csv=args.h16_block_lut_csv,
        h16_diff_csv=args.h16_diff_csv,
        h12_reference_csv=args.h12_reference_csv,
        h12_block_lut_csv=args.h12_block_lut_csv,
        h12_diff_csv=args.h12_diff_csv,
        output_dir=args.output_dir,
        output_stem=args.output_stem,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
