"""Plot Round 32 Fig. 2: BER overlap with decode-time inset.

Inputs are existing R31 real-OFEC CSVs. This script does not run simulation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REF = ROOT / "results" / "raw" / "round31_fig4_real_ofec_syndrome_lut_ber.csv"
DEFAULT_LUT = ROOT / "results" / "raw" / "round31_fig4_real_ofec_block_lut_ber.csv"
DEFAULT_DIFF = ROOT / "results" / "raw" / "round31_fig4_real_ofec_curve_diff.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round32_fig2_ber_decode_inset"


def compute_decode_speedup(reference_csv: Path, block_lut_csv: Path) -> dict[str, float]:
    ref = pd.read_csv(reference_csv)
    lut = pd.read_csv(block_lut_csv)
    merged = ref[["snr_db", "decode_sec"]].merge(
        lut[["snr_db", "decode_sec"]], on="snr_db", suffixes=("_reference", "_block_lut")
    )
    merged = merged[merged["decode_sec_block_lut"] > 0]
    ratios = merged["decode_sec_reference"] / merged["decode_sec_block_lut"]
    return {
        "decode_speedup": float(merged["decode_sec_reference"].sum() / merged["decode_sec_block_lut"].sum()),
        "point_min_speedup": float(ratios.min()),
        "point_max_speedup": float(ratios.max()),
        "points": float(len(merged)),
    }


def _save(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def plot_fig2(
    reference_csv: Path = DEFAULT_REF,
    block_lut_csv: Path = DEFAULT_LUT,
    diff_csv: Path = DEFAULT_DIFF,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    ref = pd.read_csv(reference_csv)
    lut = pd.read_csv(block_lut_csv)
    diff = pd.read_csv(diff_csv)
    stats = compute_decode_speedup(reference_csv, block_lut_csv)
    all_matched = bool(diff["matched"].all()) if "matched" in diff.columns and len(diff) else False

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 11, "axes.labelsize": 10})
    fig, ax = plt.subplots(figsize=(5.7, 3.6))
    for df, label, color, marker in (
        (ref, "reference backend", "#777777", "s"),
        (lut, "block-LUT backend", "#2AA6A1", "o"),
    ):
        solid = df[df["post_fec_errors"] >= 10] if "post_fec_errors" in df.columns else df
        open_rows = df[df["post_fec_errors"] < 10] if "post_fec_errors" in df.columns else df.iloc[0:0]
        ax.plot(solid["snr_db"], solid["post_fec_ber"], marker=marker, color=color, linewidth=1.7, label=label)
        if len(open_rows):
            ax.plot(
                open_rows["snr_db"],
                open_rows["post_fec_ber"],
                marker=marker,
                linestyle="",
                color=color,
                markerfacecolor="white",
                markeredgewidth=1.5,
            )
    ax.set_yscale("log")
    ax.set_xlabel("SNR Es/N0 (dB)")
    ax.set_ylabel("Post-FEC BER")
    ax.set_title("BER overlap with decode-time inset")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper right", frameon=True)

    inset = ax.inset_axes([0.09, 0.08, 0.29, 0.27])
    totals = [pd.read_csv(reference_csv)["decode_sec"].sum(), pd.read_csv(block_lut_csv)["decode_sec"].sum()]
    inset.bar([0, 1], totals, color=["#777777", "#2AA6A1"], width=0.55)
    inset.set_xticks([0, 1], ["ref", "LUT"], fontsize=7)
    inset.set_title("decode time", fontsize=7, pad=1)
    inset.tick_params(axis="y", labelsize=7)
    inset.grid(True, axis="y", alpha=0.2)
    ax.text(
        0.05,
        0.45,
        f"{'0 mismatches' if all_matched else 'diff present'}\n"
        f"decode {stats['decode_speedup']:.2f}x\n"
        f"range {stats['point_min_speedup']:.2f}-{stats['point_max_speedup']:.2f}x",
        transform=ax.transAxes,
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#888888", "alpha": 0.9},
    )
    _save(fig, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round32 Fig2 BER with decode-time inset.")
    parser.add_argument("--reference-csv", type=Path, default=DEFAULT_REF)
    parser.add_argument("--block-lut-csv", type=Path, default=DEFAULT_LUT)
    parser.add_argument("--diff-csv", type=Path, default=DEFAULT_DIFF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig2(args.reference_csv, args.block_lut_csv, args.diff_csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
