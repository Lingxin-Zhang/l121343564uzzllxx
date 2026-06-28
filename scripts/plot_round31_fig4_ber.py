"""Merge and plot Round 31 real-OFEC BER curve.

The script reuses the existing h=16 deep points and merges in newly measured
low-SNR shoulder points. The zero-error 14.0 dB point is intentionally excluded
from the plotted formal curve.
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
DEFAULT_EXISTING_REFERENCE = RAW_DIR / "round30_fig4_h16_formal_6h_real_ofec_syndrome_lut_ber.csv"
DEFAULT_EXISTING_BLOCK_LUT = RAW_DIR / "round30_fig4_h16_formal_6h_real_ofec_block_lut_ber.csv"
DEFAULT_LOW_REFERENCE = RAW_DIR / "round31_fig4_low_snr_real_ofec_syndrome_lut_ber.csv"
DEFAULT_LOW_BLOCK_LUT = RAW_DIR / "round31_fig4_low_snr_real_ofec_block_lut_ber.csv"
DEFAULT_DIFF = RAW_DIR / "round31_fig4_real_ofec_curve_diff.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
DEFAULT_MERGED_OUTPUT_DIR = RAW_DIR
OUTPUT_STEM = "round31_fig4_real_ofec_ber"


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _is_plotted_snr(row: dict[str, Any]) -> bool:
    snr = round(float(row["snr_db"]), 2)
    return 13.50 <= snr <= 13.95


def merge_curve_rows(low_rows: list[dict[str, Any]], existing_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_snr: dict[float, dict[str, Any]] = {}
    for row in low_rows + existing_rows:
        if not _is_plotted_snr(row):
            continue
        by_snr[round(float(row["snr_db"]), 2)] = dict(row)
    return [by_snr[snr] for snr in sorted(by_snr)]


def _paired_diff(reference_rows: list[dict[str, Any]], block_lut_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lut_by_snr = {round(float(row["snr_db"]), 2): row for row in block_lut_rows}
    rows = []
    for ref in reference_rows:
        snr = round(float(ref["snr_db"]), 2)
        lut = lut_by_snr[snr]
        post_errors_delta = int(lut["post_fec_errors"]) - int(ref["post_fec_errors"])
        post_ber_delta = float(lut["post_fec_ber"]) - float(ref["post_fec_ber"])
        rows.append(
            {
                "snr_db": f"{snr:.2f}",
                "matched": str(post_errors_delta == 0 and post_ber_delta == 0.0),
                "post_fec_errors_delta": post_errors_delta,
                "post_fec_ber_delta": post_ber_delta,
            }
        )
    return rows


def _setup_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "figure.dpi": 160,
        }
    )


def _save(fig: plt.Figure, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.7)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def _curve(rows: list[dict[str, Any]]) -> tuple[list[float], list[float], list[int]]:
    ordered = sorted(rows, key=lambda row: float(row["snr_db"]))
    return (
        [float(row["snr_db"]) for row in ordered],
        [float(row["post_fec_ber"]) for row in ordered],
        [int(row["post_fec_errors"]) for row in ordered],
    )


def plot_round31_fig4(
    *,
    existing_reference_csv: Path = DEFAULT_EXISTING_REFERENCE,
    existing_block_lut_csv: Path = DEFAULT_EXISTING_BLOCK_LUT,
    low_reference_csv: Path = DEFAULT_LOW_REFERENCE,
    low_block_lut_csv: Path = DEFAULT_LOW_BLOCK_LUT,
    diff_csv: Path = DEFAULT_DIFF,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    merged_output_dir: Path = DEFAULT_MERGED_OUTPUT_DIR,
) -> None:
    _setup_style()
    reference_rows = merge_curve_rows(read_csv_rows(low_reference_csv), read_csv_rows(existing_reference_csv))
    block_lut_rows = merge_curve_rows(read_csv_rows(low_block_lut_csv), read_csv_rows(existing_block_lut_csv))
    diff_rows = _paired_diff(reference_rows, block_lut_rows)
    _write_csv(merged_output_dir / "round31_fig4_real_ofec_syndrome_lut_ber.csv", reference_rows)
    _write_csv(merged_output_dir / "round31_fig4_real_ofec_block_lut_ber.csv", block_lut_rows)
    _write_csv(diff_csv, diff_rows)

    ref_x, ref_y, ref_errors = _curve(reference_rows)
    lut_x, lut_y, lut_errors = _curve(block_lut_rows)
    fig, ax = plt.subplots(figsize=(5.2, 3.25))
    ax.plot(ref_x, ref_y, color="#777777", linewidth=2.6, marker="s", alpha=0.72, label="reference backend")
    ax.plot(lut_x, lut_y, color="#2AA6A1", linewidth=1.25, linestyle="--", marker="o", label="block-LUT backend")
    for x, y, errors in zip(lut_x, lut_y, lut_errors):
        if errors < 10:
            ax.scatter([x], [y], facecolors="white", edgecolors="#8B1A1A", s=55, zorder=5)
    mismatches = sum(1 for row in diff_rows if row["matched"] != "True")
    ax.text(
        0.03,
        0.05,
        f"{mismatches} mismatches across {len(diff_rows)} paired points",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#777777"},
    )
    if any(error < 10 for error in ref_errors):
        ax.text(
            0.03,
            0.15,
            "open marker: low-confidence tail, <10 events",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7,
            color="#333333",
        )
    ax.set_yscale("log")
    ax.set_xlabel("SNR Es/N0 (dB)")
    ax.set_ylabel("Post-FEC BER")
    ax.set_title("Real OFEC BER, h=16")
    ax.grid(True, which="both", alpha=0.24, linewidth=0.55)
    ax.legend(frameon=True, loc="best")
    _save(fig, output_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round 31 real OFEC BER.")
    parser.add_argument("--existing-reference-csv", type=Path, default=DEFAULT_EXISTING_REFERENCE)
    parser.add_argument("--existing-block-lut-csv", type=Path, default=DEFAULT_EXISTING_BLOCK_LUT)
    parser.add_argument("--low-reference-csv", type=Path, default=DEFAULT_LOW_REFERENCE)
    parser.add_argument("--low-block-lut-csv", type=Path, default=DEFAULT_LOW_BLOCK_LUT)
    parser.add_argument("--diff-csv", type=Path, default=DEFAULT_DIFF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--merged-output-dir", type=Path, default=DEFAULT_MERGED_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_round31_fig4(
        existing_reference_csv=args.existing_reference_csv,
        existing_block_lut_csv=args.existing_block_lut_csv,
        low_reference_csv=args.low_reference_csv,
        low_block_lut_csv=args.low_block_lut_csv,
        diff_csv=args.diff_csv,
        output_dir=args.output_dir,
        merged_output_dir=args.merged_output_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
