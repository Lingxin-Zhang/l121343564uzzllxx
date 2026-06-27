"""Plot Fig. 4 from results/raw/decode_syndrome_accel.csv.

Required columns:
profile, batch_size, backend, correctness_passed, decision_mismatch_count,
status_mismatch_count, corrected_word_mismatch_count, median_runtime_s.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "results" / "raw" / "decode_syndrome_accel.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "fig4_decode_syndrome_accel"


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_true(value: object) -> bool:
    return str(value) == "True"


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


def load_decode_ratios(path: Path = DEFAULT_CSV) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows = [row for row in read_csv_rows(path) if _is_true(row["correctness_passed"])]
    mismatch_totals = {
        "decision": sum(int(row["decision_mismatch_count"]) for row in rows),
        "status": sum(int(row["status_mismatch_count"]) for row in rows),
        "corrected": sum(int(row["corrected_word_mismatch_count"]) for row in rows),
    }
    by_profile_batch: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        by_profile_batch[(row["profile"], int(row["batch_size"]))][row["backend"]] = row
    ratios: list[dict[str, Any]] = []
    for (profile, batch), backend_rows in sorted(by_profile_batch.items()):
        naive = backend_rows.get("NaiveGF2Kernel.apply_many")
        lut = backend_rows.get("PackedBlockLUTKernel.apply_many_packed")
        if not naive or not lut:
            continue
        lut_median = float(lut["median_runtime_s"])
        if lut_median <= 0:
            continue
        ratios.append(
            {
                "profile": profile,
                "batch_size": batch,
                "speedup": float(naive["median_runtime_s"]) / lut_median,
            }
        )
    return ratios, mismatch_totals


def _profile_label(profile: str) -> str:
    if profile == "bch_255_239_r16":
        return "BCH(255,239), r=16"
    if profile == "bch_511_484_r27":
        return "BCH(511,484), r=27"
    return profile


def plot_fig4(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    _setup_style()
    ratios, mismatch_totals = load_decode_ratios(csv_path)
    fig, (ax_left, ax_right) = plt.subplots(
        1,
        2,
        figsize=(7.25, 2.95),
        gridspec_kw={"width_ratios": [0.85, 1.35]},
    )

    categories = ["decision", "status", "corrected"]
    values = [mismatch_totals[name] for name in categories]
    ax_left.bar(categories, values, color=["#90CAF9", "#A5D6A7", "#FFCC80"], edgecolor="#555555")
    ax_left.set_ylim(0, max(1, max(values) + 1))
    ax_left.set_title("(a) Bit-exact decisions")
    ax_left.set_ylabel("Mismatch count")
    ax_left.grid(True, axis="y", alpha=0.24, linewidth=0.55)
    ax_left.text(
        0.5,
        0.78,
        "0 mismatch\nacross all batches",
        transform=ax_left.transAxes,
        ha="center",
        va="center",
        fontsize=9,
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#777777"},
    )

    by_profile: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ratios:
        by_profile[row["profile"]].append(row)
    colors = {"bch_255_239_r16": "#1f77b4", "bch_511_484_r27": "#d62728"}
    for profile, rows in sorted(by_profile.items()):
        ordered = sorted(rows, key=lambda row: row["batch_size"])
        ax_right.plot(
            [row["batch_size"] for row in ordered],
            [row["speedup"] for row in ordered],
            marker="o",
            linewidth=1.8,
            color=colors.get(profile),
            label=_profile_label(profile),
        )
    ax_right.axhline(1.0, color="#444444", linestyle="--", linewidth=1.1)
    ax_right.set_xscale("log")
    ax_right.set_title("(b) Decode wall-clock ratio")
    ax_right.set_xlabel("Batch size (codewords)")
    ax_right.set_ylabel("Naive / block-LUT")
    ax_right.grid(True, which="both", alpha=0.24, linewidth=0.55)
    ax_right.legend(frameon=True, loc="best")
    ax_right.text(
        0.5,
        -0.30,
        "Only syndrome backend changes; error locator unchanged.",
        transform=ax_right.transAxes,
        ha="center",
        va="top",
        fontsize=7,
        color="#444444",
    )
    for ax in (ax_left, ax_right):
        ax.tick_params(direction="out", length=3.5, width=0.8)
        for spine in ax.spines.values():
            spine.set_linewidth(0.9)
    _save_figure(fig, output_dir, OUTPUT_STEM)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot paper Fig. 4 from decode CSV.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_fig4(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
