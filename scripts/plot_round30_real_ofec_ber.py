"""Plot Round 30 real-OFEC BER from paired backend CSVs.

Required CSV inputs:
- results/raw/round30_real_ofec_syndrome_lut_ber.csv
- results/raw/round30_real_ofec_block_lut_ber.csv
- results/raw/round30_real_ofec_curve_diff.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
DEFAULT_REFERENCE_CSV = RAW_DIR / "round30_real_ofec_syndrome_lut_ber.csv"
DEFAULT_BLOCK_LUT_CSV = RAW_DIR / "round30_real_ofec_block_lut_ber.csv"
DEFAULT_DIFF_CSV = RAW_DIR / "round30_real_ofec_curve_diff.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round30_real_ofec_ber"


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_curve_match_count(path: Path = DEFAULT_DIFF_CSV) -> int:
    rows = read_csv_rows(path)
    return sum(1 for row in rows if str(row["matched"]) == "True")


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "figure.dpi": 160,
        }
    )


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.7)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{stem}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _curve(rows: list[dict[str, Any]]) -> tuple[list[float], list[float], list[str]]:
    ordered = sorted(rows, key=lambda row: float(row["snr_db"]))
    snr = [float(row["snr_db"]) for row in ordered]
    ber = [float(row["post_fec_ber"]) for row in ordered]
    stop = [str(row["stop_reason"]) for row in ordered]
    return snr, ber, stop


def plot_round30_real_ofec_ber(
    *,
    reference_csv: Path = DEFAULT_REFERENCE_CSV,
    block_lut_csv: Path = DEFAULT_BLOCK_LUT_CSV,
    diff_csv: Path = DEFAULT_DIFF_CSV,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> None:
    _setup_style()
    reference_rows = read_csv_rows(reference_csv)
    block_lut_rows = read_csv_rows(block_lut_csv)
    diff_rows = read_csv_rows(diff_csv)
    matched_count = sum(1 for row in diff_rows if str(row["matched"]) == "True")
    mismatch_count = len(diff_rows) - matched_count

    ref_snr, ref_ber, ref_stop = _curve(reference_rows)
    lut_snr, lut_ber, lut_stop = _curve(block_lut_rows)

    fig, ax = plt.subplots(figsize=(4.9, 3.2))
    ax.plot(
        ref_snr,
        ref_ber,
        marker="s",
        linewidth=1.25,
        color="#777777",
        alpha=0.72,
        label="reference backend",
    )
    ax.plot(
        lut_snr,
        lut_ber,
        marker="o",
        linewidth=1.8,
        color="#2AA6A1",
        label="block-LUT backend",
    )
    for snr, ber, stop in zip(lut_snr, lut_ber, lut_stop):
        if stop in {"time_capped", "max_blocks_reached"}:
            ax.scatter([snr], [ber], marker="^", s=38, color="#8B1A1A", zorder=4)

    ax.set_yscale("log")
    ax.set_xlabel("SNR Es/N0 (dB)")
    ax.set_ylabel("Post-FEC BER")
    ax.set_title("Real OFEC BER, h=10")
    ax.grid(True, which="both", alpha=0.24, linewidth=0.55)
    ax.tick_params(direction="out", length=3.5, width=0.8)
    ax.legend(frameon=True, loc="best")
    ax.text(
        0.03,
        0.05,
        f"{mismatch_count} mismatches across {len(diff_rows)} paired points",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#777777"},
    )
    if ref_stop != lut_stop:
        ax.text(
            0.03,
            0.15,
            "stop reasons differ",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7,
            color="#8B1A1A",
        )
    for spine in ax.spines.values():
        spine.set_linewidth(0.9)
    _save_figure(fig, output_dir, OUTPUT_STEM)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round 30 real OFEC BER.")
    parser.add_argument("--reference-csv", type=Path, default=DEFAULT_REFERENCE_CSV)
    parser.add_argument("--block-lut-csv", type=Path, default=DEFAULT_BLOCK_LUT_CSV)
    parser.add_argument("--diff-csv", type=Path, default=DEFAULT_DIFF_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_round30_real_ofec_ber(
        reference_csv=args.reference_csv,
        block_lut_csv=args.block_lut_csv,
        diff_csv=args.diff_csv,
        output_dir=args.output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
