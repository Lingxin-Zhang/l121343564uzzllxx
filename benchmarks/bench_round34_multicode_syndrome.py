"""Round34 multi-code, three-backend BCH syndrome throughput benchmark.

This runner measures the same fixed GF(2) syndrome map ``v H^T`` for four BCH
profiles and three online backends.  It keeps one CSV row per timed repeat so
the raw timing samples remain available for review.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import time
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs
from benchmarks.bench_fixed_map_three_backend import (
    BackendSpec,
    _as_gf2_matrix,
    _force_single_thread_env,
    _make_backend_specs,
    _make_chunks,
    _parse_int_list,
    environment_fields,
    pack_batch,
)
from benchmarks.bench_round31_cache_width import (
    DEFAULT_PROFILES,
    _frequency_lock_status,
    _parse_profile_keys,
    _try_set_affinity,
    build_round31_matrix_specs,
    lut_table_bytes,
    predict_cache_widths,
)
from linear_kernel import NaiveGF2Kernel

DEFAULT_BATCH_SIZES = (100, 300, 500, 700, 1_000, 1_500, 2_000, 3_000, 5_000, 10_000)
DEFAULT_REPEATS = 10
DEFAULT_WARMUPS = 30
DEFAULT_MAX_IN_MEMORY_ROWS = 10_000
DEFAULT_TIME_BUDGET_S = 20 * 60
DEFAULT_OUTPUT = RAW_DIR / "round34_multicode_three_backend_syndrome_rounds.csv"
DEFAULT_SUMMARY_OUTPUT = RAW_DIR / "round34_multicode_three_backend_syndrome_summary.csv"
DEFAULT_BLOCK_WIDTH_SOURCE = RAW_DIR / "round32_cache_width_decision_summary.csv"

DISPLAY_BACKEND_ORDER = (
    "galois_per_codeword",
    "PackedBatchGF2Kernel.apply_many",
    "PackedBlockLUTKernel.apply_many_packed",
)

RAW_FIELDNAMES = [
    "profile",
    "task",
    "backend",
    "baseline_role",
    "batch_size",
    "round_index",
    "input_width",
    "output_width",
    "processed_bits",
    "block_width",
    "block_width_source",
    "lut_table_bytes",
    "packed_word_bits",
    "sample_runtime_s",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "correctness_passed",
    "timed",
    "skip_reason",
    "exactness_elapsed_s",
    "warmups",
    "repeats",
    "build_init_s",
    "elapsed_config_s",
    "affinity_status",
    "frequency_lock_status",
    "galois_available",
    "galois_version",
    "cpu_model",
    "l1d_bytes",
    "l2_bytes",
    "l3_bytes",
    "python_version",
    "numpy_version",
    "thread_count",
    "seed",
    "notes",
]

SUMMARY_FIELDNAMES = [
    "profile",
    "task",
    "backend",
    "baseline_role",
    "batch_size",
    "representative_batch_size",
    "is_representative_batch",
    "input_width",
    "output_width",
    "processed_bits",
    "block_width",
    "block_width_source",
    "lut_table_bytes",
    "packed_word_bits",
    "median_runtime_s",
    "min_runtime_s",
    "max_runtime_s",
    "stdev_runtime_s",
    "cv",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "round_count",
    "correctness_passed",
    "timed",
    "skip_reason",
    "warmups",
    "repeats",
    "build_init_s",
    "affinity_status",
    "frequency_lock_status",
    "galois_available",
    "galois_version",
    "cpu_model",
    "l1d_bytes",
    "l2_bytes",
    "l3_bytes",
    "python_version",
    "numpy_version",
    "thread_count",
    "seed",
    "notes",
]


def _read_round32_best_widths(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    widths: dict[str, int] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profile = row.get("profile", "")
            best_w = row.get("best_w", "")
            if profile and best_w:
                widths[profile] = int(float(best_w))
    return widths


def _select_block_width(profile: str, input_width: int, output_width: int, source: Path) -> tuple[int, str]:
    if profile == "bch_255_239_r16":
        return 14, "fixed_round34_r16_w14"
    measured = _read_round32_best_widths(source)
    if profile in measured:
        return measured[profile], f"round32_cache_width_decision_summary:{source.name}"
    predicted = predict_cache_widths(input_width, output_width)["L2"]
    return int(predicted), "predicted_max_l2_fit"


def _summary(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "median_runtime_s": 0.0,
            "min_runtime_s": 0.0,
            "max_runtime_s": 0.0,
            "stdev_runtime_s": 0.0,
            "cv": 0.0,
        }
    mean = statistics.fmean(samples)
    stdev = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "median_runtime_s": statistics.median(samples),
        "min_runtime_s": min(samples),
        "max_runtime_s": max(samples),
        "stdev_runtime_s": stdev,
        "cv": stdev / mean if mean > 0 else 0.0,
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def summarize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("timed")) != "True":
            continue
        key = (str(row["profile"]), str(row["task"]), str(row["backend"]), int(row["batch_size"]))
        grouped.setdefault(key, []).append(row)

    summary_rows: list[dict[str, Any]] = []
    for (_, _, _, _), group_rows in grouped.items():
        first = group_rows[0]
        samples = [float(row["sample_runtime_s"]) for row in group_rows]
        stats = _summary(samples)
        median = stats["median_runtime_s"]
        batch_size = int(first["batch_size"])
        processed_bits = int(first["processed_bits"])
        copied = {
            **{field: first.get(field, "") for field in SUMMARY_FIELDNAMES},
            **stats,
            "throughput_Mbit_s": processed_bits / median / 1_000_000.0 if median > 0 else 0.0,
            "throughput_Mcodeword_s": batch_size / median / 1_000_000.0 if median > 0 else 0.0,
            "round_count": len(group_rows),
            "correctness_passed": all(str(row.get("correctness_passed")) == "True" for row in group_rows),
            "timed": True,
            "skip_reason": "",
        }
        summary_rows.append(copied)

    representative: dict[str, int] = {}
    for profile in sorted({str(row["profile"]) for row in summary_rows}):
        lut_rows = [
            row
            for row in summary_rows
            if row["profile"] == profile and row["backend"] == "PackedBlockLUTKernel.apply_many_packed"
        ]
        if not lut_rows:
            continue
        best = max(lut_rows, key=lambda row: float(row["throughput_Mbit_s"]))
        representative[profile] = int(best["batch_size"])

    for row in summary_rows:
        rep = representative.get(str(row["profile"]), "")
        row["representative_batch_size"] = rep
        row["is_representative_batch"] = bool(rep != "" and int(row["batch_size"]) == int(rep))

    order = {backend: idx for idx, backend in enumerate(DISPLAY_BACKEND_ORDER)}
    summary_rows.sort(key=lambda row: (str(row["profile"]), int(row["batch_size"]), order.get(str(row["backend"]), 99)))
    return [{field: row.get(field, "") for field in SUMMARY_FIELDNAMES} for row in summary_rows]


def _exactness_for_backend(backend: BackendSpec, matrix: np.ndarray, batch: np.ndarray) -> tuple[bool, float]:
    start = time.perf_counter()
    reference = NaiveGF2Kernel(matrix).apply_many(batch)
    expected = pack_batch(reference) if backend.output_mode == "packed" else reference
    actual = backend.fn(batch)
    return bool(np.array_equal(actual, expected)), time.perf_counter() - start


def _bench_config(
    *,
    spec: Any,
    matrix: np.ndarray,
    backend: BackendSpec,
    batch_size: int,
    block_width: int,
    block_width_source: str,
    rng: np.random.Generator,
    env: dict[str, Any],
    seed: int,
    warmups: int,
    repeats: int,
    max_in_memory_rows: int,
    affinity_status: str,
    frequency_lock_status: str,
) -> list[dict[str, Any]]:
    config_start = time.perf_counter()
    input_width, output_width = matrix.shape
    chunks, chunked, chunk_size = _make_chunks(
        input_width=input_width,
        batch_size=batch_size,
        max_in_memory_rows=max_in_memory_rows,
        rng=rng,
    )
    correctness_passed, exactness_elapsed_s = _exactness_for_backend(backend, matrix, chunks[0])
    processed_bits = int(batch_size) * int(input_width)
    common = {
        "profile": spec.profile,
        "task": "syndrome",
        "backend": backend.backend,
        "baseline_role": backend.baseline_role,
        "batch_size": int(batch_size),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "processed_bits": processed_bits,
        "block_width": int(block_width) if backend.backend == "PackedBlockLUTKernel.apply_many_packed" else "",
        "block_width_source": block_width_source if backend.backend == "PackedBlockLUTKernel.apply_many_packed" else "",
        "lut_table_bytes": lut_table_bytes(input_width, output_width, block_width)
        if backend.backend == "PackedBlockLUTKernel.apply_many_packed"
        else "",
        "packed_word_bits": 16 if output_width <= 16 else 32,
        "correctness_passed": correctness_passed,
        "warmups": int(warmups),
        "repeats": int(repeats),
        "build_init_s": float(spec.init_elapsed_s),
        "affinity_status": affinity_status,
        "frequency_lock_status": frequency_lock_status,
        **env,
        "seed": int(seed),
        "notes": f"{backend.notes}; chunked_online={chunked}; chunk_size={chunk_size}",
    }
    if not correctness_passed:
        row = {
            **common,
            "round_index": "",
            "sample_runtime_s": "",
            "throughput_Mbit_s": 0.0,
            "throughput_Mcodeword_s": 0.0,
            "timed": False,
            "skip_reason": "exactness failed",
            "exactness_elapsed_s": exactness_elapsed_s,
            "elapsed_config_s": time.perf_counter() - config_start,
        }
        return [{field: row.get(field, "") for field in RAW_FIELDNAMES}]

    for _ in range(int(warmups)):
        for chunk in chunks:
            backend.fn(chunk)

    rows: list[dict[str, Any]] = []
    for round_index in range(int(repeats)):
        start = time.perf_counter()
        for chunk in chunks:
            backend.fn(chunk)
        runtime = time.perf_counter() - start
        row = {
            **common,
            "round_index": int(round_index),
            "sample_runtime_s": runtime,
            "throughput_Mbit_s": processed_bits / runtime / 1_000_000.0 if runtime > 0 else 0.0,
            "throughput_Mcodeword_s": int(batch_size) / runtime / 1_000_000.0 if runtime > 0 else 0.0,
            "timed": True,
            "skip_reason": "",
            "exactness_elapsed_s": exactness_elapsed_s,
            "elapsed_config_s": time.perf_counter() - config_start,
        }
        rows.append({field: row.get(field, "") for field in RAW_FIELDNAMES})
    return rows


def run_round34_rows(
    *,
    profiles: tuple[str, ...] = DEFAULT_PROFILES,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    max_in_memory_rows: int = DEFAULT_MAX_IN_MEMORY_ROWS,
    seed: int = 42,
    cpu_core: int | None = None,
    time_budget_s: float = DEFAULT_TIME_BUDGET_S,
    block_width_source: Path = DEFAULT_BLOCK_WIDTH_SOURCE,
) -> list[dict[str, Any]]:
    _force_single_thread_env()
    env = environment_fields()
    if not env["galois_available"]:
        raise RuntimeError("galois is required for the naive per-codeword baseline")
    affinity_status = _try_set_affinity(cpu_core)
    frequency_lock_status = _frequency_lock_status()
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    start = time.perf_counter()
    specs = build_round31_matrix_specs(profiles)
    for spec in specs:
        matrix = _as_gf2_matrix(spec.matrix)
        block_width, width_source = _select_block_width(spec.profile, matrix.shape[0], matrix.shape[1], block_width_source)
        backends = _make_backend_specs(
            spec=spec,
            task="syndrome",
            matrix=matrix,
            block_width=block_width,
            include_galois=True,
            max_galois_batch_size=max(batch_sizes),
        )
        for batch_size in batch_sizes:
            for backend in backends:
                if time_budget_s > 0 and time.perf_counter() - start > time_budget_s:
                    return rows
                rows.extend(
                    _bench_config(
                        spec=spec,
                        matrix=matrix,
                        backend=backend,
                        batch_size=int(batch_size),
                        block_width=block_width,
                        block_width_source=width_source,
                        rng=rng,
                        env=env,
                        seed=seed,
                        warmups=warmups,
                        repeats=repeats,
                        max_in_memory_rows=max_in_memory_rows,
                        affinity_status=affinity_status,
                        frequency_lock_status=frequency_lock_status,
                    )
                )
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Round34 multi-code syndrome throughput benchmark.")
    parser.add_argument("--profiles", default=",".join(DEFAULT_PROFILES))
    parser.add_argument("--batch-sizes", default=",".join(str(v) for v in DEFAULT_BATCH_SIZES))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu-core", type=int, default=None)
    parser.add_argument("--time-budget-s", type=float, default=DEFAULT_TIME_BUDGET_S)
    parser.add_argument("--block-width-source", type=Path, default=DEFAULT_BLOCK_WIDTH_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_SUMMARY_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_round34_rows(
        profiles=_parse_profile_keys(args.profiles),
        batch_sizes=_parse_int_list(args.batch_sizes),
        repeats=args.repeats,
        warmups=args.warmups,
        max_in_memory_rows=args.max_in_memory_rows,
        seed=args.seed,
        cpu_core=args.cpu_core,
        time_budget_s=args.time_budget_s,
        block_width_source=args.block_width_source,
    )
    if not rows:
        raise RuntimeError("no rows were measured")
    _write_csv(args.output, rows, RAW_FIELDNAMES)
    summary = summarize_rows(rows)
    _write_csv(args.summary_output, summary, SUMMARY_FIELDNAMES)
    print(f"wrote {args.output}")
    print(f"wrote {args.summary_output}")
    failed = [row for row in rows if str(row.get("correctness_passed")) != "True"]
    if failed:
        print(f"WARNING: {len(failed)} raw rows failed exactness")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
