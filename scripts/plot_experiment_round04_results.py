"""Generate diagnostic figures for supplemental experiment round 04."""

from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
FIGURE_DIR = ROOT / "results" / "figures"

COLORS = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00"]


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
        fig.savefig(output, dpi=240, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def plot_component_decoder_exactness() -> None:
    rows = _read_csv(RAW_DIR / "component_decoder_exactness.csv")
    test_cases = [
        "all_zero",
        "all_single_bit_errors",
        "all_double_bit_errors",
        "sampled_triple_bit_errors",
        "random_error_batch",
        "random_received_batch",
    ]
    backends = sorted({row["syndrome_backend"] for row in rows})
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["test_case"], row["syndrome_backend"])].append(
            float(row["latency_per_word_us"])
        )

    x = np.arange(len(test_cases), dtype=float)
    width = 0.78 / max(1, len(backends))
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for index, backend in enumerate(backends):
        offsets = x - 0.39 + width / 2 + index * width
        values = [_mean(grouped[(case, backend)]) for case in test_cases]
        ax.bar(
            offsets,
            values,
            width=width,
            color=COLORS[index % len(COLORS)],
            edgecolor="white",
            linewidth=0.5,
            label=backend,
        )
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(test_cases, rotation=20, ha="right")
    ax.set_xlabel("component decoder exactness case")
    ax.set_ylabel("Latency per word (us)")
    ax.set_title("Component decoder exactness diagnostic")
    ax.grid(True, axis="y", alpha=0.25, linestyle="--")
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    _save(fig, "experiment_round04_component_decoder_exactness")


def main() -> None:
    plot_component_decoder_exactness()


if __name__ == "__main__":
    main()
