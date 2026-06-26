"""Export final paper-facing figures, tables, and artifact metadata."""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
SUMMARY_DIR = ROOT / "results" / "summary"
FIGURE_DIR = ROOT / "results" / "paper_figures_final"
FINAL_SUMMARY_DIR = ROOT / "results" / "summary"
PROVENANCE_OUTPUT = ROOT / "results" / "raw" / "artifact_provenance.json"

COLORS = {
    "blue": "#2F5F9F",
    "green": "#2E8B57",
    "orange": "#C46A27",
    "red": "#B5423A",
    "purple": "#6F5AA7",
    "gray": "#666666",
    "light_gray": "#D8D8D8",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format(row.get(field, "")) for field in fieldnames})
    print(f"wrote {path}")


def _format(value: Any) -> Any:
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return f"{value:.6g}"
    return value


def _float(row: dict[str, Any], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, ""))
    except (TypeError, ValueError):
        return default


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _safe_name(name: str) -> str:
    return (
        name.replace("PackedBlockLUT.apply_many_packed", "PackedBlockLUT")
        .replace("PackedBlockLUT.apply_many", "PackedBlockLUT")
        .replace("PackedBatch.apply_many", "PackedBatch")
        .replace("Naive.apply_many", "Naive")
        .replace("SparseXor.apply_many", "SparseXor")
        .replace("event_update.batch_update_many", "EventUpdate")
        .replace("from_scratch.PackedBlockLUT.apply_many_packed", "From scratch")
    )


def setup_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 9.5,
            "axes.labelsize": 8.5,
            "legend.fontsize": 7,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "lines.linewidth": 1.5,
            "lines.markersize": 4.0,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def save_figure(fig: plt.Figure, figure_dir: Path, stem: str) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(pad=0.6)
    for suffix in ("png", "pdf"):
        output = figure_dir / f"{stem}.{suffix}"
        fig.savefig(output, dpi=300, bbox_inches="tight")
        print(f"wrote {output}")
    plt.close(fig)


def _plot_lines(ax: plt.Axes, groups: dict[str, list[tuple[float, float]]]) -> None:
    palette = [COLORS["blue"], COLORS["green"], COLORS["orange"], COLORS["purple"], COLORS["red"]]
    for idx, (label, pairs) in enumerate(sorted(groups.items())):
        ordered = sorted(pairs)
        ax.plot(
            [x for x, _ in ordered],
            [y for _, y in ordered],
            marker="o",
            color=palette[idx % len(palette)],
            label=_safe_name(label),
        )


def build_final_exactness_table(summary_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    rows = read_csv(summary_dir / "component_decoder_exactness_summary.csv")
    selected = [row for row in rows if row.get("preset") == "full"]
    out = [
        {
            "test_case": row["test_case"],
            "code_profile": row["code_profile"],
            "syndrome_backend": row["syndrome_backend"],
            "num_words": row["num_words"],
            "double_error_coverage": row["double_error_coverage"],
            "num_possible_double_errors": row["num_possible_double_errors"],
            "exact_mismatch_count": row["exact_mismatch_count"],
            "correctness_all_true": row["correctness_all_true"],
            "mean_latency_per_word_us": row["mean_latency_per_word_us"],
            "source_csv": "results/summary/component_decoder_exactness_summary.csv",
        }
        for row in selected
    ]
    write_csv(
        output_dir / "final_exactness_table.csv",
        out,
        [
            "test_case",
            "code_profile",
            "syndrome_backend",
            "num_words",
            "double_error_coverage",
            "num_possible_double_errors",
            "exact_mismatch_count",
            "correctness_all_true",
            "mean_latency_per_word_us",
            "source_csv",
        ],
    )
    return out


def build_final_claim_audit(output_dir: Path) -> list[dict[str, str]]:
    rows = [
        {
            "claim": "GF(2) backend outputs are bit-exact for tested matrices and workloads.",
            "supporting_files": "tests/test_correctness.py; results/summary/*_summary.csv",
            "supporting_fields": "correctness_all_true; correctness_passed",
            "recommended_wording": "All accelerated GF(2) kernel backends are checked against a naive matrix-vector reference on the tested workloads.",
            "current_status": "supported",
            "cautions": "Scope is tested kernels and matrices, not a full decoder.",
        },
        {
            "claim": "Component-decoder decisions are exact in the tested component model.",
            "supporting_files": "results/summary/component_decoder_exactness_summary.csv",
            "supporting_fields": "exact_mismatch_count=0; correctness_all_true=True; all_double_bit_errors",
            "recommended_wording": "The component decision path preserves decoded word, correction mask, and status over full double-error coverage.",
            "current_status": "supported",
            "cautions": "No BER or full OFEC decoder claim.",
        },
        {
            "claim": "PackedBlockLUT is effective for candidate-heavy syndrome computation.",
            "supporting_files": "results/summary/candidate_testing_summary.csv",
            "supporting_fields": "mean_latency_per_candidate_us; correctness_all_true",
            "recommended_wording": "Packed LUT evaluation reduces per-candidate syndrome cost for candidate-heavy batches while preserving exact syndrome outputs.",
            "current_status": "supported",
            "cautions": "Use candidate-testing wording, not full Chase decoder wording.",
        },
        {
            "claim": "EventUpdate accelerates low-flip syndrome updates.",
            "supporting_files": "results/summary/event_update_summary.csv",
            "supporting_fields": "relative_to_from_scratch_packed; flip_count",
            "recommended_wording": "For low-flip updates, incremental syndrome updates avoid full recomputation and reduce per-word update latency.",
            "current_status": "supported",
            "cautions": "Do not mix update-from-zero candidate testing with real event update claims.",
        },
        {
            "claim": "CacheAwarePlanner tracks the measured oracle on major workloads.",
            "supporting_files": "results/summary/cache_aware_selection_workload_summary.csv",
            "supporting_fields": "mean_planner_over_oracle; p90_planner_over_oracle; backend match rates",
            "recommended_wording": "The cache-footprint-guided planner stays close to the measured oracle across representative GF(2) kernel workloads.",
            "current_status": "supported",
            "cautions": "Not a theoretical optimal scheduler.",
        },
        {
            "claim": "Block width creates a latency-memory/cache trade-off.",
            "supporting_files": "results/summary/cache_aware_summary.csv; results/summary/long_stream_cache_width_summary.csv",
            "supporting_fields": "block_width; lut_bytes; fits_l1/fits_l2/fits_l3; latency",
            "recommended_wording": "The best LUT block width depends on the latency-memory trade-off and the cache tier that the LUT footprint reaches.",
            "current_status": "supported",
            "cautions": "Use profile-specific wording.",
        },
        {
            "claim": "Long-stream cache-width behavior is profile and workload dependent.",
            "supporting_files": "results/summary/long_stream_cache_width_summary.csv; results/summary/long_stream_cache_width_replication_summary.csv",
            "supporting_fields": "best_cache_level; best_l2_over_best_l1; best_l3_over_best_l1",
            "recommended_wording": "Long-stream measurements show that the preferred cache tier changes with the component profile and iteration regime.",
            "current_status": "supported",
            "cautions": "Do not claim L2/L3 universally dominate L1.",
        },
        {
            "claim": "The eBCH-like long-stream workload shows condition-specific L3 advantage.",
            "supporting_files": "results/summary/long_stream_cache_width_summary.csv; results/summary/long_stream_cache_width_replication_summary.csv",
            "supporting_fields": "l3_strong_20x_claim=True",
            "recommended_wording": "In the tested eBCH-like long-stream regime, an L3-fitting LUT width passes the 20x, stable 20% gate against the best L1-fitting width.",
            "current_status": "condition-specific",
            "cautions": "Only for the tested eBCH-like long-stream condition.",
        },
        {
            "claim": "L2 evidence is promising but mixed.",
            "supporting_files": "results/summary/long_stream_cache_width_summary.csv; results/summary/long_stream_cache_width_replication_summary.csv",
            "supporting_fields": "l2_strong_20x_claim",
            "recommended_wording": "L2-fitting widths can be favorable in selected eBCH-like long-stream measurements, but the evidence is mixed across runs.",
            "current_status": "mixed",
            "cautions": "Do not write L2 as a stable strong claim.",
        },
        {
            "claim": "Optical trace workload results are kernel-call evidence.",
            "supporting_files": "results/summary/optical_workloads_summary.csv",
            "supporting_fields": "executed_*; aggregate_latency_per_executed_unit_us",
            "recommended_wording": "Trace-level workloads exercise component-kernel call patterns representative of optical-FEC processing.",
            "current_status": "supporting",
            "cautions": "Not a full decoder or BER simulation.",
        },
        {
            "claim": "The method is decision-preserving rather than BER-improving.",
            "supporting_files": "results/summary/final_exactness_table.csv",
            "supporting_fields": "exact_mismatch_count=0; correctness_all_true=True",
            "recommended_wording": "The acceleration replaces exact GF(2) component-kernel computations and is therefore decision-preserving for the tested component model.",
            "current_status": "supported",
            "cautions": "Do not claim BER improvement.",
        },
    ]
    write_csv(
        output_dir / "final_claim_audit.csv",
        rows,
        [
            "claim",
            "supporting_files",
            "supporting_fields",
            "recommended_wording",
            "current_status",
            "cautions",
        ],
    )
    return rows


def _best_by_latency(rows: Iterable[dict[str, str]], metric: str) -> dict[str, str] | None:
    clean = [row for row in rows if not math.isnan(_float(row, metric))]
    return min(clean, key=lambda row: _float(row, metric)) if clean else None


def build_final_representative_table(summary_dir: Path, output_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    exact = read_csv(summary_dir / "component_decoder_exactness_summary.csv")
    double_rows = [
        r
        for r in exact
        if r["preset"] == "full"
        and r["test_case"] == "all_double_bit_errors"
        and r["syndrome_backend"] == "HybridPlanner.apply_many_packed"
    ]
    if double_rows:
        r = double_rows[0]
        rows.append(
            _representative(
                "Component exactness",
                "all_double_bit_errors",
                r["syndrome_backend"],
                "NaiveGF2Kernel.apply_many",
                f"exact_mismatch_count={r['exact_mismatch_count']}; num_words={r['num_words']}",
                "decision-preserving exactness",
                r["correctness_all_true"],
                "results/summary/component_decoder_exactness_summary.csv",
            )
        )

    candidates = [
        r
        for r in read_csv(summary_dir / "candidate_testing_summary.csv")
        if r["preset"] == "full"
        and r["target_mode"] == "known_hit"
        and r["backend"] == "PackedBlockLUT.apply_many_packed"
    ]
    best_candidate = _best_by_latency(candidates, "mean_latency_per_candidate_us")
    if best_candidate:
        rows.append(
            _representative(
                "Candidate testing",
                f"{best_candidate['code_profile']} candidates={best_candidate['candidate_count']}",
                best_candidate["backend"],
                "Naive.apply_many",
                f"{best_candidate['mean_latency_per_candidate_us']} us/candidate",
                "candidate-heavy syndrome cost",
                best_candidate["correctness_all_true"],
                "results/summary/candidate_testing_summary.csv",
            )
        )

    events = [
        r
        for r in read_csv(summary_dir / "event_update_summary.csv")
        if r["method"] == "event_update.batch_update_many" and r["flip_count"] == "1"
    ]
    best_event = _best_by_latency(events, "mean_latency_per_word_us")
    if best_event:
        rows.append(
            _representative(
                "Event update",
                "flip_count=1",
                "EventUpdate.update_many",
                "from_scratch.PackedBlockLUT",
                f"{best_event['mean_latency_per_word_us']} us/word; x{best_event['relative_to_from_scratch_packed']}",
                "low-flip update",
                best_event["correctness_all_true"],
                "results/summary/event_update_summary.csv",
            )
        )

    planner = [
        r
        for r in read_csv(summary_dir / "cache_aware_selection_workload_summary.csv")
        if r["preset"] == "paper"
    ]
    if planner:
        mean_ratio = sum(_float(r, "mean_planner_over_oracle") for r in planner) / len(planner)
        max_ratio = max(_float(r, "max_planner_over_oracle") for r in planner)
        rows.append(
            _representative(
                "CacheAwarePlanner",
                "paper workload set",
                "CacheAwarePlanner",
                "measured oracle",
                f"mean planner/oracle={mean_ratio:.3f}; max={max_ratio:.3f}",
                "near-oracle backend choice",
                all(_truthy(r["correctness_all_true"]) for r in planner),
                "results/summary/cache_aware_selection_workload_summary.csv",
            )
        )

    for experiment, path, metric, condition_key in (
        (
            "BCH syndrome throughput",
            "bch_syndrome_summary.csv",
            "mean_throughput_Mbit_s",
            "total_bits",
        ),
        (
            "Component loop scaling",
            "component_loop_summary.csv",
            "mean_throughput_Mbit_s",
            "num_words",
        ),
    ):
        source_rows = read_csv(summary_dir / path)
        best = max(source_rows, key=lambda r: _float(r, metric)) if source_rows else None
        if best:
            rows.append(
                _representative(
                    experiment,
                    f"{condition_key}={best[condition_key]}; iter={best['iterations']}",
                    best["backend"],
                    "Naive.apply_many",
                    f"{best[metric]} Mbit/s",
                    "component-kernel scaling",
                    best.get("correctness_all_true", "True"),
                    f"results/summary/{path}",
                )
            )

    long_rows = read_csv(summary_dir / "long_stream_cache_width_replication_summary.csv")
    ebch = next((r for r in long_rows if r["code_profile"] == "ebch_256_239_r17"), None)
    if ebch:
        rows.append(
            _representative(
                "Long-stream cache width",
                f"{ebch['code_profile']} bits={ebch['stream_input_bits']}",
                f"{ebch['best_cache_level']} width {ebch['best_block_width']}",
                f"L1 width {ebch['best_l1_block_width']}",
                f"L3/L1={ebch['best_l3_over_best_l1']}; L2/L1={ebch['best_l2_over_best_l1']}",
                "cache-width trade-off",
                ebch["correctness_all_true"],
                "results/summary/long_stream_cache_width_replication_summary.csv",
            )
        )

    cache_rows = [
        r
        for r in read_csv(summary_dir / "cache_aware_summary.csv")
        if r["backend"] == "PackedBlockLUT.apply_many_packed"
        and r["code_profile"] == "bch_255_239_r16"
        and r["batch_size"] == "4096"
        and r["density"] == "0.05"
    ]
    cache_best = _best_by_latency(cache_rows, "mean_latency_per_word_us")
    if cache_best:
        rows.append(
            _representative(
                "Cache/memory trade-off",
                "bch_255_239_r16 batch=4096 density=0.05",
                f"PackedBlockLUT width {cache_best['block_width']}",
                "other block widths",
                f"{cache_best['mean_latency_per_word_us']} us/word; LUT={cache_best['lut_bytes']} bytes",
                "block-width memory trade-off",
                cache_best["correctness_all_true"],
                "results/summary/cache_aware_summary.csv",
            )
        )

    write_csv(
        output_dir / "final_representative_table.csv",
        rows,
        [
            "experiment",
            "profile_or_workload",
            "best_or_selected_backend",
            "reference_backend",
            "latency_or_throughput_metric",
            "speedup_or_planner_oracle_ratio",
            "correctness",
            "source_csv",
        ],
    )
    return rows


def _representative(
    experiment: str,
    profile_or_workload: str,
    best_backend: str,
    reference_backend: str,
    metric: str,
    ratio: str,
    correctness: Any,
    source_csv: str,
) -> dict[str, Any]:
    return {
        "experiment": experiment,
        "profile_or_workload": profile_or_workload,
        "best_or_selected_backend": best_backend,
        "reference_backend": reference_backend,
        "latency_or_throughput_metric": metric,
        "speedup_or_planner_oracle_ratio": ratio,
        "correctness": correctness,
        "source_csv": source_csv,
    }


def plot_cache_memory_tradeoff(summary_dir: Path, figure_dir: Path) -> None:
    cache_rows = [
        r
        for r in read_csv(summary_dir / "cache_aware_summary.csv")
        if r["backend"] == "PackedBlockLUT.apply_many_packed"
        and r["cache_profile"] == "generic_desktop"
        and r["batch_size"] == "4096"
        and r["density"] == "0.05"
        and r["code_profile"] in {"bch_255_239_r16", "ebch_256_239_r17"}
    ]
    long_rows = read_csv(summary_dir / "long_stream_cache_width_summary.csv") + read_csv(
        summary_dir / "long_stream_cache_width_replication_summary.csv"
    )

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.35))
    ax = axes[0]
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in cache_rows:
        groups[row["code_profile"]].append(
            (_float(row, "block_width"), _float(row, "mean_latency_per_word_us"))
        )
    _plot_lines(ax, groups)
    ax.set_xlabel("Block width")
    ax.set_ylabel("Latency / word (us)")
    ax.set_title("(a) Latency")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[1]
    for profile, label_rows in sorted(
        {
            row["code_profile"]: [r for r in cache_rows if r["code_profile"] == row["code_profile"]]
            for row in cache_rows
        }.items()
    ):
        by_width = {}
        for row in label_rows:
            by_width[_float(row, "block_width")] = _float(row, "lut_bytes")
        ax.plot(
            sorted(by_width),
            [by_width[x] for x in sorted(by_width)],
            marker="o",
            label=profile,
        )
    for value, label in ((32768, "L1"), (1048576, "L2"), (16777216, "L3")):
        ax.axhline(value, color=COLORS["gray"], linestyle="--", linewidth=0.8)
        ax.text(4.1, value * 1.08, label, fontsize=6.5, color=COLORS["gray"])
    ax.set_yscale("log")
    ax.set_xlabel("Block width")
    ax.set_ylabel("LUT bytes")
    ax.set_title("(b) Footprint")
    ax.grid(True, axis="y", alpha=0.25)

    ax = axes[2]
    selected = [
        r
        for r in long_rows
        if r["iterations"] == "5"
        and r["code_profile"] in {"bch_255_239_r16", "ebch_256_239_r17"}
    ]
    labels = [f"{r['code_profile'].replace('_', ' ')}\n{r['best_cache_level']}" for r in selected]
    x = list(range(len(labels)))
    width = 0.34
    ax.bar(
        [pos - width / 2 for pos in x],
        [_float(r, "best_l2_over_best_l1") for r in selected],
        width=width,
        color=COLORS["green"],
        label="L2/L1",
    )
    ax.bar(
        [pos + width / 2 for pos in x],
        [_float(r, "best_l3_over_best_l1") for r in selected],
        width=width,
        color=COLORS["orange"],
        label="L3/L1",
    )
    ax.axhline(1.0, color=COLORS["gray"], linestyle="--", linewidth=0.8)
    ax.axhline(0.8, color=COLORS["red"], linestyle=":", linewidth=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right")
    ax.set_ylabel("Latency ratio")
    ax.set_title("(c) Long stream")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2, loc="upper right")
    save_figure(fig, figure_dir, "fig_cache_memory_tradeoff")


def plot_cache_aware_planner(summary_dir: Path, figure_dir: Path) -> None:
    rows = [
        r
        for r in read_csv(summary_dir / "cache_aware_selection_workload_summary.csv")
        if r["preset"] == "paper"
    ]
    rows = sorted(rows, key=lambda r: r["workload_type"])
    labels = [_workload_label(r["workload_type"]) for r in rows]
    x = list(range(len(rows)))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.45))
    ax = axes[0]
    width = 0.25
    for offset, key, label, color in (
        (-width, "mean_planner_over_oracle", "mean", COLORS["blue"]),
        (0.0, "p90_planner_over_oracle", "p90", COLORS["green"]),
        (width, "max_planner_over_oracle", "max", COLORS["orange"]),
    ):
        ax.bar([pos + offset for pos in x], [_float(r, key) for r in rows], width, label=label, color=color)
    ax.axhline(1.0, color=COLORS["gray"], linestyle="--", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Planner / oracle latency")
    ax.set_title("(a) Latency ratio")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper left")

    ax = axes[1]
    ax.bar(
        [pos - width / 2 for pos in x],
        [_float(r, "oracle_match_rate_backend_only") for r in rows],
        width,
        color=COLORS["purple"],
        label="backend",
    )
    ax.bar(
        [pos + width / 2 for pos in x],
        [_float(r, "oracle_match_rate_backend_and_block") for r in rows],
        width,
        color=COLORS["gray"],
        label="backend+width",
    )
    ax.set_ylim(0, 1.05)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("Oracle match rate")
    ax.set_title("(b) Selection match")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)
    save_figure(fig, figure_dir, "fig_cache_aware_planner_oracle")


def _workload_label(value: str) -> str:
    return {
        "candidate_test_packed": "candidate",
        "component_decode_batch": "component",
        "dense_batch": "dense",
        "event_update": "update",
        "sparse_single": "sparse",
    }.get(value, value)


def plot_candidate_testing(summary_dir: Path, figure_dir: Path) -> None:
    rows = [
        r
        for r in read_csv(summary_dir / "candidate_testing_summary.csv")
        if r["preset"] == "full"
        and r["target_mode"] == "known_hit"
        and r["code_profile"] == "bch_255_239_r16"
        and r["backend"] in {
            "Naive.apply_many",
            "PackedBlockLUT.apply_many_packed",
            "HybridPlanner.apply_many_packed",
        }
    ]
    by_backend: dict[str, dict[float, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_backend[row["backend"]][_float(row, "candidate_count")].append(
            _float(row, "mean_latency_per_candidate_us")
        )
    fig, ax = plt.subplots(figsize=(3.6, 2.55))
    for backend, by_count in sorted(by_backend.items()):
        x = []
        y = []
        for count, values in sorted(by_count.items()):
            x.append(count)
            y.append(sum(values) / len(values))
        ax.plot(x, y, marker="o", label=_safe_name(backend))
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Candidate count")
    ax.set_ylabel("Latency / candidate (us)")
    ax.set_title("Candidate-heavy syndrome testing")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)
    save_figure(fig, figure_dir, "fig_candidate_testing")


def plot_event_update(summary_dir: Path, figure_dir: Path) -> None:
    rows = [
        r
        for r in read_csv(summary_dir / "event_update_summary.csv")
        if r["iterations"] == "10"
        and r["method"]
        in {
            "from_scratch.PackedBlockLUT.apply_many_packed",
            "event_update.batch_update_many",
            "event_update.loop_update",
        }
    ]
    by_method: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        by_method[row["method"]].append(
            (_float(row, "flip_count"), _float(row, "mean_latency_per_word_us"))
        )
    fig, ax = plt.subplots(figsize=(3.6, 2.55))
    _plot_lines(ax, by_method)
    ax.set_xlabel("Flip count")
    ax.set_ylabel("Latency / word (us)")
    ax.set_title("Low-flip syndrome update")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)
    save_figure(fig, figure_dir, "fig_event_update_comparison")


def plot_component_kernel_scaling(summary_dir: Path, figure_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.45))
    syndrome = [
        r
        for r in read_csv(summary_dir / "bch_syndrome_summary.csv")
        if r["matrix_source"] == "galois_systematic_candidate"
        and r["iterations"] == "10"
        and r["backend"] in {"Naive.apply_many", "PackedBlockLUT.apply_many_packed", "PackedBatch.apply_many"}
    ]
    groups: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in syndrome:
        groups[row["backend"]].append(
            (_float(row, "total_bits"), _float(row, "mean_throughput_Mbit_s"))
        )
    ax = axes[0]
    _plot_lines(ax, groups)
    ax.set_xscale("log")
    ax.set_xlabel("Total bits")
    ax.set_ylabel("Throughput (Mbit/s)")
    ax.set_title("(a) Syndrome stream")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)

    component = [
        r
        for r in read_csv(summary_dir / "component_loop_summary.csv")
        if r["iterations"] == "10"
        and r["backend"] in {"Naive.apply_many", "PackedBlockLUT.apply_many_packed", "PackedBatch.apply_many"}
    ]
    groups = defaultdict(list)
    for row in component:
        groups[row["backend"]].append(
            (_float(row, "num_words"), _float(row, "mean_throughput_Mbit_s"))
        )
    ax = axes[1]
    _plot_lines(ax, groups)
    ax.set_xscale("log", base=2)
    ax.set_xlabel("Component words")
    ax.set_ylabel("Throughput (Mbit/s)")
    ax.set_title("(b) Component loop")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(frameon=False)
    save_figure(fig, figure_dir, "fig_component_kernel_scaling")


def write_figure_manifest(figure_dir: Path) -> None:
    rows = [
        (
            "fig_cache_memory_tradeoff",
            "cache_aware_summary.csv; long_stream_cache_width*_summary.csv",
            "latency, LUT bytes, L2/L3 vs L1 ratio",
            "Block width creates a cache/memory trade-off; long-stream optimum is profile dependent.",
            "main text",
            "Uses stream_input_bits and true stream_input_bytes; L2 mixed, L3 condition-specific.",
        ),
        (
            "fig_cache_aware_planner_oracle",
            "cache_aware_selection_workload_summary.csv",
            "planner/oracle ratio, oracle match rate",
            "CacheAwarePlanner tracks measured oracle across representative workloads.",
            "main text",
            "Emphasizes latency ratio over exact block-width match.",
        ),
        (
            "fig_candidate_testing",
            "candidate_testing_summary.csv",
            "latency per candidate",
            "PackedBlockLUT helps candidate-heavy syndrome testing.",
            "supporting",
            "Candidate-kernel result only, not a full Chase decoder.",
        ),
        (
            "fig_event_update_comparison",
            "event_update_summary.csv",
            "latency per word vs flip_count",
            "EventUpdate reduces low-flip syndrome-update cost.",
            "main text",
            "Uses focused scaling data.",
        ),
        (
            "fig_component_kernel_scaling",
            "bch_syndrome_summary.csv; component_loop_summary.csv",
            "throughput vs total_bits/num_words",
            "Packed kernels improve component-kernel scaling.",
            "main text",
            "Component-kernel evidence, not BER.",
        ),
    ]
    lines = [
        "# Final Figure Manifest",
        "",
        "| Figure | Source CSV | Main metric | Claim supported | Paper role | Notes |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.extend(
        [
            "",
            "## Old Figures Not Recommended For Main Text",
            "",
            "- `experiment_round02_optical_workloads`: trace-level diagnostic; useful as backup only.",
            "- `fig_planner_latency`: older dispatcher diagnostic; replaced by `fig_cache_aware_planner_oracle`.",
            "- raw diagnostic block-width figures: replaced by `fig_cache_memory_tradeoff`.",
        ]
    )
    output = figure_dir / "figure_manifest.md"
    figure_dir.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


def write_artifact_provenance(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    code_commit = _git(["rev-parse", "--short", "HEAD"]) or "unknown"
    dirty_paths = _git(["status", "--short"]).splitlines()
    data = {
        "code_commit_hash": code_commit,
        "current_commit_hash": code_commit,
        "git_dirty": bool(dirty_paths),
        "generated_after_commit": bool(dirty_paths),
        "dirty_reason": (
            "Generated artifact files and review notes may be present before final commit."
            if dirty_paths
            else "clean"
        ),
        "dirty_paths_summary": dirty_paths[:50],
        "generated_artifact_dirs": [
            "results/summary",
            "results/paper_figures_final",
            "review_gpt",
        ],
        "hardware_profile_path": "results/raw/hardware_profile.json",
        "notes": "No local absolute paths are required to interpret these artifacts.",
    }
    output.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"wrote {output}")


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def export_all(
    *,
    raw_dir: Path,
    summary_dir: Path,
    figure_dir: Path,
    final_summary_dir: Path,
    provenance_output: Path,
) -> None:
    setup_style()
    final_summary_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)

    build_final_exactness_table(summary_dir, final_summary_dir)
    build_final_claim_audit(final_summary_dir)
    build_final_representative_table(summary_dir, final_summary_dir)

    plot_cache_memory_tradeoff(summary_dir, figure_dir)
    plot_cache_aware_planner(summary_dir, figure_dir)
    plot_candidate_testing(summary_dir, figure_dir)
    plot_event_update(summary_dir, figure_dir)
    plot_component_kernel_scaling(summary_dir, figure_dir)
    write_figure_manifest(figure_dir)
    write_artifact_provenance(provenance_output)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export final paper figures and tables.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--summary-dir", type=Path, default=SUMMARY_DIR)
    parser.add_argument("--figure-dir", type=Path, default=FIGURE_DIR)
    parser.add_argument("--final-summary-dir", type=Path, default=FINAL_SUMMARY_DIR)
    parser.add_argument("--provenance-output", type=Path, default=PROVENANCE_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    export_all(
        raw_dir=args.raw_dir,
        summary_dir=args.summary_dir,
        figure_dir=args.figure_dir,
        final_summary_dir=args.final_summary_dir,
        provenance_output=args.provenance_output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
