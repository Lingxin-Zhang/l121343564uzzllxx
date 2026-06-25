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


def summarize_cache_aware_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "cache_profile",
        "code_profile",
        "matrix_shape",
        "n",
        "r",
        "backend",
        "block_width",
        "batch_size",
        "density",
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
                "std_latency_per_word_us": _std(
                    _float(row, "latency_per_word_us") for row in group
                ),
                "std_throughput_Mword_s": _std(
                    _float(row, "throughput_Mword_s") for row in group
                ),
                "lut_bytes": int(max(_float(row, "lut_bytes", 0.0) for row in group)),
                "num_blocks": int(max(_float(row, "num_blocks", 0.0) for row in group)),
                "entries_per_block": int(
                    max(_float(row, "entries_per_block", 0.0) for row in group)
                ),
                "fits_l1": all(_truthy(row.get("fits_l1", "True")) for row in group),
                "fits_l2": all(_truthy(row.get("fits_l2", "True")) for row in group),
                "fits_l3": all(_truthy(row.get("fits_l3", "True")) for row in group),
                "l1d_bytes": int(max(_float(row, "l1d_bytes", 0.0) for row in group)),
                "l2_bytes": int(max(_float(row, "l2_bytes", 0.0) for row in group)),
                "l3_bytes": int(max(_float(row, "l3_bytes", 0.0) for row in group)),
                "cache_line_bytes": int(
                    max(_float(row, "cache_line_bytes", 0.0) for row in group)
                ),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_cache_aware_selection_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "code_profile",
        "cache_profile",
        "workload_type",
        "batch_size",
        "density_or_weight",
        "output_mode",
        "selected_backend",
        "selected_block_width",
        "oracle_best_backend",
        "oracle_best_block_width",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "selection_reason": next((row.get("selection_reason", "") for row in group), ""),
                "lut_bytes": int(max(_float(row, "lut_bytes", 0.0) for row in group)),
                "fits_l1": all(_truthy(row.get("fits_l1", "True")) for row in group),
                "fits_l2": all(_truthy(row.get("fits_l2", "True")) for row in group),
                "fits_l3": all(_truthy(row.get("fits_l3", "True")) for row in group),
                "mean_selected_latency_us": _mean(
                    _float(row, "selected_latency_us") for row in group
                ),
                "mean_oracle_best_latency_us": _mean(
                    _float(row, "oracle_best_latency_us") for row in group
                ),
                "mean_planner_over_oracle": _mean(
                    _float(row, "planner_over_oracle") for row in group
                ),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_code_profile_scaling_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "code_profile",
        "verification_status",
        "matrix_kind",
        "is_synthetic",
        "matrix_shape",
        "n",
        "r",
        "backend",
        "batch_size",
        "density",
        "block_width",
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
                "std_latency_per_word_us": _std(
                    _float(row, "latency_per_word_us") for row in group
                ),
                "std_throughput_Mword_s": _std(
                    _float(row, "throughput_Mword_s") for row in group
                ),
                "packed_word_bits": int(
                    max(_float(row, "packed_word_bits", 0.0) for row in group)
                ),
                "packed_dtype": next((row.get("packed_dtype", "") for row in group), ""),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_candidate_testing_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "target_mode",
        "code_profile",
        "pattern_type",
        "p_chase",
        "candidate_weight",
        "candidate_count",
        "backend",
        "output_mode",
        "selected_backend",
        "selected_backend_reason",
        "block_width",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_latency_per_candidate_us": _mean(
                    _float(row, "latency_per_candidate_us") for row in group
                ),
                "mean_throughput_Mcandidate_s": _mean(
                    _float(row, "throughput_Mcandidate_s") for row in group
                ),
                "std_latency_per_candidate_us": _std(
                    _float(row, "latency_per_candidate_us") for row in group
                ),
                "std_throughput_Mcandidate_s": _std(
                    _float(row, "throughput_Mcandidate_s") for row in group
                ),
                "matches_found": int(max(_float(row, "matches_found", 0.0) for row in group)),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_component_decoder_exactness_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "code_profile",
        "test_case",
        "syndrome_backend",
        "num_words",
        "double_error_coverage",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "num_possible_double_errors": int(
                    max(_float(row, "num_possible_double_errors", 0.0) for row in group)
                ),
                "exact_mismatch_count": int(
                    max(_float(row, "exact_mismatch_count", 0.0) for row in group)
                ),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "mean_latency_per_word_us": _mean(
                    _float(row, "latency_per_word_us") for row in group
                ),
                "mean_throughput_Mword_s": _mean(
                    _float(row, "throughput_Mword_s") for row in group
                ),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_optical_workload_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "workload_type",
        "code_profile",
        "num_blocks",
        "window_len",
        "num_iterations_or_steps",
        "backend_or_method",
        "block_width",
        "batch_size",
        "density",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "intended_syndrome_calls": int(
                    max(_float(row, "intended_syndrome_calls", 0.0) for row in group)
                ),
                "executed_syndrome_calls": int(
                    max(_float(row, "executed_syndrome_calls", 0.0) for row in group)
                ),
                "intended_candidate_tests": int(
                    max(_float(row, "intended_candidate_tests", 0.0) for row in group)
                ),
                "executed_candidate_tests": int(
                    max(_float(row, "executed_candidate_tests", 0.0) for row in group)
                ),
                "intended_event_updates": int(
                    max(_float(row, "intended_event_updates", 0.0) for row in group)
                ),
                "executed_event_updates": int(
                    max(_float(row, "executed_event_updates", 0.0) for row in group)
                ),
                "num_syndrome_calls": int(
                    max(_float(row, "num_syndrome_calls", 0.0) for row in group)
                ),
                "num_candidate_tests": int(
                    max(_float(row, "num_candidate_tests", 0.0) for row in group)
                ),
                "num_executed_candidate_tests": int(
                    max(_float(row, "num_executed_candidate_tests", 0.0) for row in group)
                ),
                "num_event_updates": int(
                    max(_float(row, "num_event_updates", 0.0) for row in group)
                ),
                "mean_total_runtime_s": _mean(
                    _float(row, "total_runtime_s") for row in group
                ),
                "mean_aggregate_latency_per_executed_unit_us": _mean(
                    _float(row, "aggregate_latency_per_executed_unit_us") for row in group
                ),
                "mean_throughput_Mexecuted_unit_s": _mean(
                    _float(row, "throughput_Mexecuted_unit_s") for row in group
                ),
                "std_aggregate_latency_per_executed_unit_us": _std(
                    _float(row, "aggregate_latency_per_executed_unit_us") for row in group
                ),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "notes": next((row.get("notes", "") for row in group), ""),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_optical_workload_breakdown_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    keys = (
        "preset",
        "workload_type",
        "code_profile",
        "task_kind",
        "backend_or_method",
        "unit_type",
    )
    summary = []
    for key, group in sorted(_group_rows(rows, keys).items()):
        summary.append(
            {
                **dict(zip(keys, key, strict=True)),
                "mean_num_units": _mean(_float(row, "num_units") for row in group),
                "mean_total_runtime_s": _mean(
                    _float(row, "total_runtime_s") for row in group
                ),
                "mean_latency_per_unit_us": _mean(
                    _float(row, "latency_per_unit_us") for row in group
                ),
                "std_latency_per_unit_us": _std(
                    _float(row, "latency_per_unit_us") for row in group
                ),
                "mean_throughput_Munit_s": _mean(
                    _float(row, "throughput_Munit_s") for row in group
                ),
                "correctness_all_true": all(
                    _truthy(row.get("correctness_passed", "True")) for row in group
                ),
                "notes": next((row.get("notes", "") for row in group), ""),
                "num_rows": len(group),
            }
        )
    return summary


def summarize_best_backend_rows(summary_by_name: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_best_from_component(summary_by_name.get("component_loop", [])))
    rows.extend(_best_from_event(summary_by_name.get("event_update", [])))
    rows.extend(_best_from_planner(summary_by_name.get("planner", [])))
    rows.extend(_best_from_bch(summary_by_name.get("bch_syndrome", [])))
    rows.extend(_best_from_cache_aware(summary_by_name.get("cache_aware", [])))
    rows.extend(_best_from_code_profile_scaling(summary_by_name.get("code_profile_scaling", [])))
    rows.extend(_best_from_candidate_testing(summary_by_name.get("candidate_testing", [])))
    rows.extend(_best_from_component_decoder_exactness(summary_by_name.get("component_decoder_exactness", [])))
    rows.extend(_best_from_optical_workloads(summary_by_name.get("optical_workloads", [])))
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


def _best_from_cache_aware(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(
        rows,
        ("preset", "code_profile", "block_width", "batch_size", "density"),
    )
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next((row for row in group if row["backend"] == "Naive.apply_many"), None)
        out.append(
            _best_row(
                "cache_aware",
                key[1],
                f"preset={key[0]};block_width={key[2]};batch_size={key[3]};density={key[4]}",
                best["backend"],
                baseline["backend"] if baseline else "",
                best,
                "mean_throughput_Mword_s",
                baseline,
            )
        )
    return out


def _best_from_code_profile_scaling(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(
        rows,
        ("preset", "code_profile", "batch_size", "density", "block_width"),
    )
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next((row for row in group if row["backend"] == "Naive.apply_many"), None)
        out.append(
            _best_row(
                "code_profile_scaling",
                key[1],
                f"preset={key[0]};batch_size={key[2]};density={key[3]};block_width={key[4]}",
                best["backend"],
                baseline["backend"] if baseline else "",
                best,
                "mean_throughput_Mword_s",
                baseline,
            )
        )
    return out


def _best_from_candidate_testing(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(
        rows,
        (
            "preset",
            "target_mode",
            "code_profile",
            "pattern_type",
            "candidate_count",
            "block_width",
        ),
    )
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_candidate_us"]))
        baseline = next((row for row in group if row["backend"] == "Naive.apply_many"), None)
        out.append(
            _best_row(
                "candidate_testing",
                key[2],
                (
                    f"preset={key[0]};target_mode={key[1]};pattern_type={key[3]};"
                    f"candidate_count={key[4]};block_width={key[5]}"
                ),
                best["backend"],
                baseline["backend"] if baseline else "",
                {
                    **best,
                    "mean_latency_per_word_us": best["mean_latency_per_candidate_us"],
                },
                "mean_throughput_Mcandidate_s",
                (
                    {**baseline, "mean_latency_per_word_us": baseline["mean_latency_per_candidate_us"]}
                    if baseline
                    else None
                ),
            )
        )
    return out


def _best_from_optical_workloads(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(
        rows,
        (
            "preset",
            "workload_type",
            "code_profile",
            "num_blocks",
            "window_len",
            "num_iterations_or_steps",
        ),
    )
    out = []
    for key, group in grouped.items():
        best = min(
            group,
            key=lambda row: float(row["mean_aggregate_latency_per_executed_unit_us"]),
        )
        baseline = next((row for row in group if row["backend_or_method"] == "Naive.apply_many"), None)
        out.append(
            _best_row(
                "optical_workloads",
                key[2],
                f"preset={key[0]};workload_type={key[1]};num_blocks={key[3]};window_len={key[4]};steps={key[5]}",
                best["backend_or_method"],
                baseline["backend_or_method"] if baseline else "",
                {
                    **best,
                    "mean_latency_per_word_us": best[
                        "mean_aggregate_latency_per_executed_unit_us"
                    ],
                },
                "mean_throughput_Mexecuted_unit_s",
                (
                    {
                        **baseline,
                        "mean_latency_per_word_us": baseline[
                            "mean_aggregate_latency_per_executed_unit_us"
                        ],
                    }
                    if baseline
                    else None
                ),
            )
        )
    return out


def _best_from_component_decoder_exactness(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = _group_rows(
        rows,
        (
            "preset",
            "code_profile",
            "test_case",
            "num_words",
        ),
    )
    out = []
    for key, group in grouped.items():
        best = min(group, key=lambda row: float(row["mean_latency_per_word_us"]))
        baseline = next(
            (row for row in group if row["syndrome_backend"] == "NaiveGF2Kernel.apply_many"),
            None,
        )
        out.append(
            _best_row(
                "component_decoder_exactness",
                key[1],
                f"preset={key[0]};test_case={key[2]};num_words={key[3]}",
                best["syndrome_backend"],
                baseline["syndrome_backend"] if baseline else "",
                best,
                "mean_throughput_Mword_s",
                baseline,
            )
        )
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
        (
            "cache_aware",
            raw_dir / "cache_aware.csv",
            summary_dir / "cache_aware_summary.csv",
            summarize_cache_aware_rows,
            [
                "preset",
                "cache_profile",
                "code_profile",
                "matrix_shape",
                "n",
                "r",
                "backend",
                "block_width",
                "batch_size",
                "density",
                "mean_latency_per_word_us",
                "mean_throughput_Mword_s",
                "std_latency_per_word_us",
                "std_throughput_Mword_s",
                "lut_bytes",
                "num_blocks",
                "entries_per_block",
                "fits_l1",
                "fits_l2",
                "fits_l3",
                "l1d_bytes",
                "l2_bytes",
                "l3_bytes",
                "cache_line_bytes",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "cache_aware_selection",
            raw_dir / "cache_aware_selection.csv",
            summary_dir / "cache_aware_selection_summary.csv",
            summarize_cache_aware_selection_rows,
            [
                "preset",
                "code_profile",
                "cache_profile",
                "workload_type",
                "batch_size",
                "density_or_weight",
                "output_mode",
                "selected_backend",
                "selected_block_width",
                "oracle_best_backend",
                "oracle_best_block_width",
                "selection_reason",
                "lut_bytes",
                "fits_l1",
                "fits_l2",
                "fits_l3",
                "mean_selected_latency_us",
                "mean_oracle_best_latency_us",
                "mean_planner_over_oracle",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "code_profile_scaling",
            raw_dir / "code_profile_scaling.csv",
            summary_dir / "code_profile_scaling_summary.csv",
            summarize_code_profile_scaling_rows,
            [
                "preset",
                "code_profile",
                "verification_status",
                "matrix_kind",
                "is_synthetic",
                "matrix_shape",
                "n",
                "r",
                "backend",
                "batch_size",
                "density",
                "block_width",
                "mean_latency_per_word_us",
                "mean_throughput_Mword_s",
                "std_latency_per_word_us",
                "std_throughput_Mword_s",
                "packed_word_bits",
                "packed_dtype",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "candidate_testing",
            raw_dir / "candidate_testing.csv",
            summary_dir / "candidate_testing_summary.csv",
            summarize_candidate_testing_rows,
            [
                "preset",
                "target_mode",
                "code_profile",
                "pattern_type",
                "p_chase",
                "candidate_weight",
                "candidate_count",
                "backend",
                "output_mode",
                "selected_backend",
                "selected_backend_reason",
                "block_width",
                "mean_latency_per_candidate_us",
                "mean_throughput_Mcandidate_s",
                "std_latency_per_candidate_us",
                "std_throughput_Mcandidate_s",
                "matches_found",
                "correctness_all_true",
                "num_rows",
            ],
        ),
        (
            "component_decoder_exactness",
            raw_dir / "component_decoder_exactness.csv",
            summary_dir / "component_decoder_exactness_summary.csv",
            summarize_component_decoder_exactness_rows,
            [
                "preset",
                "code_profile",
                "test_case",
                "syndrome_backend",
                "num_words",
                "double_error_coverage",
                "num_possible_double_errors",
                "exact_mismatch_count",
                "correctness_all_true",
                "mean_latency_per_word_us",
                "mean_throughput_Mword_s",
                "num_rows",
            ],
        ),
        (
            "optical_workloads",
            raw_dir / "optical_workloads.csv",
            summary_dir / "optical_workloads_summary.csv",
            summarize_optical_workload_rows,
            [
                "preset",
                "workload_type",
                "code_profile",
                "num_blocks",
                "window_len",
                "num_iterations_or_steps",
                "backend_or_method",
                "block_width",
                "batch_size",
                "density",
                "intended_syndrome_calls",
                "executed_syndrome_calls",
                "intended_candidate_tests",
                "executed_candidate_tests",
                "intended_event_updates",
                "executed_event_updates",
                "num_syndrome_calls",
                "num_candidate_tests",
                "num_executed_candidate_tests",
                "num_event_updates",
                "mean_total_runtime_s",
                "mean_aggregate_latency_per_executed_unit_us",
                "mean_throughput_Mexecuted_unit_s",
                "std_aggregate_latency_per_executed_unit_us",
                "correctness_all_true",
                "notes",
                "num_rows",
            ],
        ),
        (
            "optical_workload_breakdown",
            raw_dir / "optical_workload_breakdown.csv",
            summary_dir / "optical_workload_breakdown_summary.csv",
            summarize_optical_workload_breakdown_rows,
            [
                "preset",
                "workload_type",
                "code_profile",
                "task_kind",
                "backend_or_method",
                "unit_type",
                "mean_num_units",
                "mean_total_runtime_s",
                "mean_latency_per_unit_us",
                "std_latency_per_unit_us",
                "mean_throughput_Munit_s",
                "correctness_all_true",
                "notes",
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
