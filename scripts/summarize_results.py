"""Summarize raw benchmark CSV files into compact review tables."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "results" / "raw"
SUMMARY_DIR = ROOT / "results" / "summary"
NOTES = "raw lightweight benchmark result; not a paper conclusion"


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
            writer.writerow({field: _format_value(row.get(field, "")) for field in fieldnames})
    print(f"wrote {path}")


def _format_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value):
            return "nan"
        return f"{value:.12g}"
    return value


def _float(row: dict[str, str], key: str, default: float = math.nan) -> float:
    try:
        return float(row.get(key, ""))
    except ValueError:
        return default


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def _group_rows(
    rows: Iterable[dict[str, str]],
    keys: tuple[str, ...],
) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(key, "") for key in keys)].append(row)
    return grouped


def _mean(values: Iterable[float]) -> float:
    values = [value for value in values if not math.isnan(value)]
    return statistics.fmean(values) if values else math.nan


def _std(values: Iterable[float]) -> float:
    values = [value for value in values if not math.isnan(value)]
    return statistics.stdev(values) if len(values) > 1 else 0.0


def _ratio(numerator: float, denominator: float) -> float:
    if math.isnan(numerator) or math.isnan(denominator) or denominator == 0:
        return math.nan
    return numerator / denominator


def summarize_bch_syndrome_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = ("matrix_source", "backend", "total_bits", "iterations")
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        latency = [_float(row, "latency_per_word_us") for row in group]
        throughput = [_float(row, "throughput_Mbit_s") for row in group]
        table_sizes = [_float(row, "table_size_bytes", 0.0) for row in group]
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_latency_per_word_us": _mean(latency),
                "mean_throughput_Mbit_s": _mean(throughput),
                "std_latency_per_word_us": _std(latency),
                "std_throughput_Mbit_s": _std(throughput),
                "table_size_bytes": int(max(table_sizes)) if table_sizes else 0,
                "num_rows": len(group),
            }
        )
    return summary


def summarize_component_loop_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = ("matrix_source", "backend", "num_words", "iterations")
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        latency = [_float(row, "latency_per_word_us") for row in group]
        table_sizes = [_float(row, "table_size_bytes", 0.0) for row in group]
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_latency_per_word_us": _mean(latency),
                "mean_throughput_Mword_s": _mean(
                    _float(row, "throughput_Mword_s") for row in group
                ),
                "mean_throughput_Mbit_s": _mean(
                    _float(row, "throughput_Mbit_s") for row in group
                ),
                "relative_to_naive": math.nan,
                "table_size_bytes": int(max(table_sizes)) if table_sizes else 0,
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    baseline = {
        (row["matrix_source"], row["num_words"], row["iterations"]): row[
            "mean_latency_per_word_us"
        ]
        for row in summary
        if row["backend"] == "Naive.apply_many"
    }
    for row in summary:
        base = baseline.get((row["matrix_source"], row["num_words"], row["iterations"]))
        row["relative_to_naive"] = _ratio(base or math.nan, row["mean_latency_per_word_us"])
    return summary


def summarize_event_update_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = ("matrix_source", "method", "flip_count", "iterations")
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_latency_per_word_us": _mean(
                    _float(row, "latency_per_word_us") for row in group
                ),
                "mean_throughput_Mupdate_s": _mean(
                    _float(row, "throughput_Mupdate_s") for row in group
                ),
                "relative_to_from_scratch_packed": math.nan,
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    baseline = {
        (row["matrix_source"], row["flip_count"], row["iterations"]): row[
            "mean_latency_per_word_us"
        ]
        for row in summary
        if row["method"] == "from_scratch.PackedBlockLUT.apply_many_packed"
    }
    for row in summary:
        base = baseline.get((row["matrix_source"], row["flip_count"], row["iterations"]))
        row["relative_to_from_scratch_packed"] = _ratio(
            base or math.nan,
            row["mean_latency_per_word_us"],
        )
    return summary


def summarize_planner_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "matrix_source",
        "workload_type",
        "backend_or_method",
        "batch_size",
        "density",
        "flip_count",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_latency_per_word_us": _mean(
                    _float(row, "latency_per_word_us") for row in group
                ),
                "mean_throughput_Mword_s": _mean(
                    _float(row, "throughput_Mword_s") for row in group
                ),
                "relative_to_best_from_scratch": math.nan,
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    baseline = {}
    for row in summary:
        baseline_name = (
            "PackedBlockLUT.apply_many_packed"
            if row["workload_type"] == "batch_syndrome"
            else "from_scratch.PackedBlockLUT.apply_many_packed"
        )
        if row["backend_or_method"] != baseline_name:
            continue
        key = (
            row["matrix_source"],
            row["workload_type"],
            row["batch_size"],
            row["density"],
            row["flip_count"],
        )
        baseline[key] = row["mean_latency_per_word_us"]
    for row in summary:
        key = (
            row["matrix_source"],
            row["workload_type"],
            row["batch_size"],
            row["density"],
            row["flip_count"],
        )
        row["relative_to_best_from_scratch"] = _ratio(
            baseline.get(key, math.nan),
            row["mean_latency_per_word_us"],
        )
    return summary


def summarize_best_backend_rows(summary_by_name: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_best_from_component(summary_by_name.get("component_loop", [])))
    rows.extend(_best_from_event(summary_by_name.get("event_update", [])))
    rows.extend(_best_from_planner(summary_by_name.get("planner", [])))
    rows.extend(_best_from_bch(summary_by_name.get("bch_syndrome", [])))
    return rows


def _best_from_component(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(rows, ("matrix_source", "num_words", "iterations"))
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next((row for row in group if row["backend"] == "Naive.apply_many"), None)
        out.append(_best_row("component_loop", key[0], f"num_words={key[1]};iterations={key[2]}", best["backend"], baseline["backend"] if baseline else "", best, "mean_throughput_Mword_s", baseline))
    return out


def _best_from_event(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(rows, ("matrix_source", "flip_count", "iterations"))
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next((row for row in group if row["method"] == "from_scratch.PackedBlockLUT.apply_many_packed"), None)
        out.append(_best_row("event_update", key[0], f"flip_count={key[1]};iterations={key[2]}", best["method"], baseline["method"] if baseline else "", best, "mean_throughput_Mupdate_s", baseline))
    return out


def _best_from_planner(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(rows, ("matrix_source", "workload_type", "batch_size", "density", "flip_count"))
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline_name = "PackedBlockLUT.apply_many_packed" if key[1] == "batch_syndrome" else "from_scratch.PackedBlockLUT.apply_many_packed"
        baseline = next((row for row in group if row["backend_or_method"] == baseline_name), None)
        out.append(_best_row(f"planner_{key[1]}", key[0], f"batch_size={key[2]};density={key[3]};flip_count={key[4]}", best["backend_or_method"], baseline["backend_or_method"] if baseline else "", best, "mean_throughput_Mword_s", baseline))
    return out


def _best_from_bch(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(rows, ("matrix_source", "total_bits", "iterations"))
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next((row for row in group if row["backend"] == "Naive.apply_many"), None)
        out.append(_best_row("bch_syndrome", key[0], f"total_bits={key[1]};iterations={key[2]}", best["backend"], baseline["backend"] if baseline else "", best, "mean_throughput_Mbit_s", baseline))
    return out


def _best_row(
    workload_family: str,
    matrix_source: str,
    condition: str,
    best_name: str,
    baseline_name: str,
    best: dict[str, Any],
    throughput_key: str,
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    baseline_latency = (
        float(baseline["mean_latency_per_word_us"]) if baseline is not None else math.nan
    )
    best_latency = float(best["mean_latency_per_word_us"])
    return {
        "workload_family": workload_family,
        "matrix_source": matrix_source,
        "condition": condition,
        "best_backend_or_method": best_name,
        "best_latency_per_word_us": best_latency,
        "best_throughput": best.get(throughput_key, math.nan),
        "baseline_backend_or_method": baseline_name,
        "relative_to_baseline": _ratio(baseline_latency, best_latency),
        "notes": NOTES,
    }


def summarize_all(raw_dir: Path, summary_dir: Path) -> None:
    summary_by_name: dict[str, list[dict[str, Any]]] = {}
    configs = [
        (
            "bch_syndrome",
            raw_dir / "bch_syndrome.csv",
            summary_dir / "bch_syndrome_summary.csv",
            summarize_bch_syndrome_rows,
            [
                "matrix_source",
                "backend",
                "total_bits",
                "iterations",
                "mean_latency_per_word_us",
                "mean_throughput_Mbit_s",
                "std_latency_per_word_us",
                "std_throughput_Mbit_s",
                "table_size_bytes",
                "num_rows",
            ],
        ),
        (
            "component_loop",
            raw_dir / "component_loop.csv",
            summary_dir / "component_loop_summary.csv",
            summarize_component_loop_rows,
            [
                "matrix_source",
                "backend",
                "num_words",
                "iterations",
                "mean_latency_per_word_us",
                "mean_throughput_Mword_s",
                "mean_throughput_Mbit_s",
                "relative_to_naive",
                "table_size_bytes",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "event_update",
            raw_dir / "event_update.csv",
            summary_dir / "event_update_summary.csv",
            summarize_event_update_rows,
            [
                "matrix_source",
                "method",
                "flip_count",
                "iterations",
                "mean_latency_per_word_us",
                "mean_throughput_Mupdate_s",
                "relative_to_from_scratch_packed",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "planner",
            raw_dir / "planner.csv",
            summary_dir / "planner_summary.csv",
            summarize_planner_rows,
            [
                "matrix_source",
                "workload_type",
                "backend_or_method",
                "batch_size",
                "density",
                "flip_count",
                "mean_latency_per_word_us",
                "mean_throughput_Mword_s",
                "relative_to_best_from_scratch",
                "correctness_all_true",
                "num_rows",
            ],
        ),
    ]
    for name, input_path, output_path, fn, fieldnames in configs:
        raw_rows = read_csv(input_path)
        if not raw_rows:
            continue
        summary_rows = fn(raw_rows)
        summary_by_name[name] = summary_rows
        write_csv(output_path, summary_rows, fieldnames)

    best_rows = summarize_best_backend_rows(summary_by_name)
    write_csv(
        summary_dir / "best_backend_by_workload.csv",
        best_rows,
        [
            "workload_family",
            "matrix_source",
            "condition",
            "best_backend_or_method",
            "best_latency_per_word_us",
            "best_throughput",
            "baseline_backend_or_method",
            "relative_to_baseline",
            "notes",
        ],
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize raw benchmark CSV files.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--summary-dir", type=Path, default=SUMMARY_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    summarize_all(args.raw_dir, args.summary_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
