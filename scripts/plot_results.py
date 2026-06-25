"""Generate benchmark figures from CSV results."""

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


def _save_figure(fig: plt.Figure, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    for suffix in ("png", "pdf"):
        output = FIGURE_DIR / f"{name}.{suffix}"
        fig.savefig(output, dpi=180, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def _group_by_backend(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_backend: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_backend[row["backend"]].append(row)
    return by_backend


def _plot_lines(
    rows: list[dict[str, Any]],
    x_key: str,
    title: str,
    xlabel: str,
    output_name: str,
    log_x: bool = False,
    log_y: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for backend, backend_rows in sorted(_group_by_backend(rows).items()):
        ordered = sorted(backend_rows, key=lambda row: float(row[x_key]))
        x = [float(row[x_key]) for row in ordered]
        y = [float(row["latency_per_word_us"]) for row in ordered]
        ax.plot(x, y, marker="o", linewidth=1.9, label=backend)

    if log_x:
        ax.set_xscale("log", base=2)
    if log_y:
        ax.set_yscale("log")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Latency per word (us)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    _save_figure(fig, output_name)


def plot_block_width() -> None:
    rows = _read_csv(RAW_DIR / "block_width.csv")
    by_backend = _group_by_backend(rows)
    fig, ax_latency = plt.subplots(figsize=(8.2, 4.8))

    block_rows = sorted(by_backend["BlockLUT"], key=lambda row: float(row["block_width"]))
    packed_block_rows = sorted(
        by_backend["PackedBlockLUT"], key=lambda row: float(row["block_width"])
    )
    block_widths = [float(row["block_width"]) for row in block_rows]
    block_latency = [float(row["latency_per_word_us"]) for row in block_rows]
    packed_block_latency = [
        float(row["latency_per_word_us"]) for row in packed_block_rows
    ]

    (block_line,) = ax_latency.plot(
        block_widths,
        block_latency,
        marker="o",
        linewidth=2.1,
        label="BlockLUT latency",
        color="tab:blue",
    )
    (packed_block_line,) = ax_latency.plot(
        block_widths,
        packed_block_latency,
        marker="o",
        linewidth=2.1,
        label="PackedBlockLUT latency",
        color="tab:purple",
    )

    latency_lines = [block_line, packed_block_line]
    for backend, color in (("Naive", "tab:orange"), ("SparseXor", "tab:green")):
        backend_rows = by_backend[backend]
        baseline = sum(float(row["latency_per_word_us"]) for row in backend_rows) / len(
            backend_rows
        )
        line = ax_latency.axhline(
            baseline,
            linestyle="--",
            linewidth=1.8,
            label=f"{backend} latency baseline",
            color=color,
        )
        latency_lines.append(line)

    ax_latency.set_title("GF(2) block-width micro-benchmark")
    ax_latency.set_xlabel("block_width")
    ax_latency.set_ylabel("Latency per word (us)")
    ax_latency.grid(True, alpha=0.25)

    ax_latency.legend(
        latency_lines,
        [line.get_label() for line in latency_lines],
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
    )
    _save_figure(fig, "block_width_vs_latency")


def plot_block_width_table_size() -> None:
    rows = _read_csv(RAW_DIR / "block_width.csv")
    by_backend = _group_by_backend(rows)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))

    for backend, color in (
        ("BlockLUT", "tab:blue"),
        ("PackedBlockLUT", "tab:purple"),
    ):
        backend_rows = sorted(
            by_backend[backend], key=lambda row: float(row["block_width"])
        )
        x = [float(row["block_width"]) for row in backend_rows]
        y = [float(row["table_size_bytes"]) for row in backend_rows]
        ax.plot(x, y, marker="s", linewidth=1.9, label=backend, color=color)

    ax.set_yscale("log")
    ax.set_title("GF(2) block-width table size")
    ax.set_xlabel("block_width")
    ax.set_ylabel("table_size_bytes")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    _save_figure(fig, "block_width_table_size")


def plot_density() -> None:
    rows = _read_csv(RAW_DIR / "density.csv")
    _plot_lines(
        rows,
        x_key="density",
        title="GF(2) density micro-benchmark",
        xlabel="density",
        output_name="density_backend_comparison",
        log_x=True,
        log_y=True,
    )


def plot_batch() -> None:
    rows = _read_csv(RAW_DIR / "batch.csv")
    _plot_lines(
        rows,
        x_key="batch_size",
        title="GF(2) batch-size micro-benchmark",
        xlabel="batch_size",
        output_name="batch_crossover",
        log_x=True,
        log_y=True,
    )


def plot_stream() -> None:
    rows = _read_csv(RAW_DIR / "stream.csv")
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    for backend, backend_rows in sorted(_group_by_backend(rows).items()):
        grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
        for row in backend_rows:
            grouped[float(row["total_bits"])].append(row)
        x = []
        y = []
        for total_bits, total_rows in sorted(grouped.items()):
            x.append(total_bits)
            y.append(
                sum(float(row["throughput_Mbit_s"]) for row in total_rows)
                / len(total_rows)
            )
        ax.plot(x, y, marker="o", linewidth=1.9, label=backend)

    ax.set_xscale("log")
    ax.set_title("GF(2) stream micro-benchmark")
    ax.set_xlabel("total_bits")
    ax.set_ylabel("throughput_Mbit_s")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=True)
    _save_figure(fig, "stream_throughput")


def main() -> None:
    plot_block_width()
    plot_block_width_table_size()
    plot_density()
    plot_batch()
    plot_stream()


if __name__ == "__main__":
    main()
