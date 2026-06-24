"""Generate initial benchmark figures from CSV results."""

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
        raise FileNotFoundError(f"missing benchmark CSV: {path}")
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _save_current(name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    for suffix in ("png", "pdf"):
        output = FIGURE_DIR / f"{name}.{suffix}"
        plt.savefig(output, dpi=180)
        print(f"wrote {output}")
    plt.close()


def _plot_series(
    rows: list[dict[str, Any]],
    x_key: str,
    y_key: str,
    title: str,
    xlabel: str,
    output_name: str,
    log_x: bool = False,
    log_y: bool = False,
) -> None:
    by_backend: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_backend[row["backend"]].append(row)

    plt.figure(figsize=(7.2, 4.4))
    for backend, backend_rows in sorted(by_backend.items()):
        ordered = sorted(backend_rows, key=lambda row: float(row[x_key]))
        x = [float(row[x_key]) for row in ordered]
        y = [float(row[y_key]) for row in ordered]
        plt.plot(x, y, marker="o", linewidth=1.8, label=backend)

    if log_x:
        plt.xscale("log", base=2)
    if log_y:
        plt.yscale("log")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("Latency per word (us)")
    plt.grid(True, alpha=0.25)
    plt.legend()
    _save_current(output_name)


def plot_block_width() -> None:
    rows = _read_csv(RAW_DIR / "block_width.csv")
    _plot_series(
        rows,
        x_key="block_width",
        y_key="latency_per_word_us",
        title="Block width vs latency",
        xlabel="Block width",
        output_name="block_width_vs_latency",
    )


def plot_density() -> None:
    rows = _read_csv(RAW_DIR / "density.csv")
    _plot_series(
        rows,
        x_key="density",
        y_key="latency_per_word_us",
        title="Density backend comparison",
        xlabel="Input density",
        output_name="density_backend_comparison",
        log_x=True,
        log_y=True,
    )


def plot_batch() -> None:
    rows = _read_csv(RAW_DIR / "batch.csv")
    _plot_series(
        rows,
        x_key="batch_size",
        y_key="latency_per_word_us",
        title="Batch size crossover",
        xlabel="Batch size",
        output_name="batch_crossover",
        log_x=True,
        log_y=True,
    )


def main() -> None:
    plot_block_width()
    plot_density()
    plot_batch()


if __name__ == "__main__":
    main()
