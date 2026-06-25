"""Generate Round 2 diagnostic figures from cache/code-profile CSVs."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
FIGURE_DIR = ROOT / "results" / "figures"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save(fig: plt.Figure, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        output = FIGURE_DIR / f"{name}.{suffix}"
        fig.savefig(output, dpi=220, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def plot_cache_aware() -> None:
    rows = _read_csv(RAW_DIR / "cache_aware.csv")
    selected = [
        row
        for row in rows
        if row["code_profile"] == "synthetic_511_r32"
        and row["batch_size"] == "4096"
        and row["density"] == "0.05"
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        grouped[row["backend"]].append(row)
    for backend, backend_rows in sorted(grouped.items()):
        ordered = sorted(backend_rows, key=lambda row: float(row["block_width"]))
        ax.plot(
            [float(row["block_width"]) for row in ordered],
            [float(row["latency_per_word_us"]) for row in ordered],
            marker="o",
            linewidth=1.8,
            label=backend,
        )
    ax.set_xlabel("block_width")
    ax.set_ylabel("Latency per word (us)")
    ax.set_title("Round 2 cache-aware diagnostic")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    _save(fig, "round2_cache_aware_latency")


def plot_code_profile_scaling() -> None:
    rows = _read_csv(RAW_DIR / "code_profile_scaling.csv")
    selected = [
        row
        for row in rows
        if row["batch_size"] == "4096" and row["density"] == "0.05"
    ]
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in selected:
        grouped[row["backend"]].append(row)
    for backend, backend_rows in sorted(grouped.items()):
        ordered = sorted(backend_rows, key=lambda row: int(row["n"]))
        ax.plot(
            [int(row["n"]) for row in ordered],
            [float(row["latency_per_word_us"]) for row in ordered],
            marker="o",
            linewidth=1.8,
            label=backend,
        )
    ax.set_xlabel("n")
    ax.set_ylabel("Latency per word (us)")
    ax.set_title("Round 2 code-profile scaling diagnostic")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    _save(fig, "round2_code_profile_scaling")


def main() -> None:
    plot_cache_aware()
    plot_code_profile_scaling()


if __name__ == "__main__":
    main()
