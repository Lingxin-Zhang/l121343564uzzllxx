"""Plot Round32 natural-vs-cache-pressure proxy control."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = ROOT / "results" / "raw" / "round32_same_tier_dram_pressure_proxy.csv"
DEFAULT_OUTPUT_DIR = ROOT / "results" / "figures"
OUTPUT_STEM = "round32_same_tier_dram_pressure_proxy"


def plot_proxy(csv_path: Path = DEFAULT_CSV, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
    df = pd.read_csv(csv_path)
    df = df[(df["timed"].astype(str) == "True") & (df["correctness_passed"].astype(str) == "True")]
    profiles = [p for p in ("bch_255_239_r16", "bch_255_231_r24") if p in set(df["profile"])]
    fig, axes = plt.subplots(1, max(1, len(profiles)), figsize=(7.2, 2.8), squeeze=False)
    for idx, profile in enumerate(profiles):
        ax = axes[0][idx]
        rows = df[df["profile"].eq(profile)]
        for mode, group in rows.groupby("measurement_mode"):
            group = group.sort_values("block_width")
            ax.plot(group["block_width"], group["throughput_Mbit_s"], marker="o", linewidth=1.4, label=mode)
        ax.set_title(profile)
        ax.set_xlabel("Block width w")
        ax.set_ylabel("Throughput (Mbit/s)")
        ax.grid(True, alpha=0.24)
        ax.legend(fontsize=7, frameon=True)
    fig.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    for suffix in ("png", "pdf"):
        path = output_dir / f"{OUTPUT_STEM}.{suffix}"
        fig.savefig(path, dpi=220, bbox_inches="tight")
        print(f"wrote {path}")
    plt.close(fig)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plot Round32 same-tier pressure proxy.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    plot_proxy(args.csv, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
