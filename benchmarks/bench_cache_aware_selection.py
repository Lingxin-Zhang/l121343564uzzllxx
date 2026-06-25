"""Cache-aware backend/block-width selection benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import statistics
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from decoders.bdd_lut import BDDLUTDecoder
from linear_kernel import (
    CacheAwarePlanner,
    EventUpdateKernel,
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    PackedBlockLUTKernel,
    SparseXorKernel,
)
from linear_kernel.cache_profile import CacheProfile, get_cache_profile
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

from ._common import RAW_DIR, ensure_result_dirs, make_batch, time_repeats

LIGHTWEIGHT_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_511_r32",
)
LIGHTWEIGHT_CACHE_PROFILES = (
    "default_cpu_cache",
    "small_l2_profile",
    "large_l3_profile",
)
LIGHTWEIGHT_WORKLOAD_TYPES = (
    "sparse_single",
    "dense_batch",
    "candidate_test_packed",
    "component_decode_batch",
    "event_update",
)
LIGHTWEIGHT_BATCH_SIZES = (1, 64, 1024, 4096)
LIGHTWEIGHT_BLOCK_WIDTHS = (4, 6, 8, 10)
PAPER_BATCH_SIZES = (1, 4, 16, 64, 256, 1024, 4096, 16384)
PAPER_BLOCK_WIDTHS = (4, 6, 8, 10, 12)
PAPER_SMALL_BATCH_SIZES = (1, 16, 64, 1024, 4096)
FULL_BATCH_SIZES = (1, 4, 16, 64, 256, 1024, 4096, 16384, 65536)
FULL_BLOCK_WIDTHS = tuple(range(4, 22, 2))
RNG_SEED = 20260802

CACHE_AWARE_SELECTION_FIELDNAMES = [
    "preset",
    "code_profile",
    "n",
    "r",
    "cache_profile",
    "workload_type",
    "batch_size",
    "density_or_weight",
    "output_mode",
    "selected_backend",
    "selected_block_width",
    "selection_reason",
    "lut_bytes",
    "fits_l1",
    "fits_l2",
    "fits_l3",
    "uses_lut",
    "cache_fit_applicable",
    "oracle_best_backend",
    "oracle_best_block_width",
    "selected_latency_us",
    "oracle_best_latency_us",
    "planner_over_oracle",
    "correctness_passed",
]


def _preset_defaults(preset: str) -> dict[str, Any]:
    if preset == "lightweight":
        return {
            "repeats": 3,
            "code_profiles": LIGHTWEIGHT_CODE_PROFILES,
            "cache_profiles": LIGHTWEIGHT_CACHE_PROFILES,
            "workload_types": LIGHTWEIGHT_WORKLOAD_TYPES,
            "batch_sizes": LIGHTWEIGHT_BATCH_SIZES,
            "block_widths": LIGHTWEIGHT_BLOCK_WIDTHS,
        }
    if preset == "paper":
        return {
            "repeats": 7,
            "code_profiles": LIGHTWEIGHT_CODE_PROFILES,
            "cache_profiles": LIGHTWEIGHT_CACHE_PROFILES,
            "workload_types": LIGHTWEIGHT_WORKLOAD_TYPES,
            "batch_sizes": PAPER_BATCH_SIZES,
            "block_widths": PAPER_BLOCK_WIDTHS,
        }
    if preset == "paper-small":
        return {
            "repeats": 5,
            "code_profiles": LIGHTWEIGHT_CODE_PROFILES,
            "cache_profiles": LIGHTWEIGHT_CACHE_PROFILES,
            "workload_types": LIGHTWEIGHT_WORKLOAD_TYPES,
            "batch_sizes": PAPER_SMALL_BATCH_SIZES,
            "block_widths": PAPER_BLOCK_WIDTHS,
        }
    if preset == "full":
        return {
            "repeats": 10,
            "code_profiles": LIGHTWEIGHT_CODE_PROFILES,
            "cache_profiles": LIGHTWEIGHT_CACHE_PROFILES,
            "workload_types": LIGHTWEIGHT_WORKLOAD_TYPES,
            "batch_sizes": FULL_BATCH_SIZES,
            "block_widths": FULL_BLOCK_WIDTHS,
        }
    raise ValueError(f"unknown preset: {preset}")


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _write_or_append_csv(path: Path, rows: list[dict[str, Any]], *, append: bool) -> None:
    if not rows:
        raise ValueError(f"no benchmark rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append and path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if mode == "w":
            writer.writeheader()
        else:
            with path.open(newline="", encoding="utf-8") as existing:
                reader = csv.reader(existing)
                existing_header = next(reader, [])
            if existing_header != list(rows[0].keys()):
                raise ValueError(
                    "cannot append cache-aware selection rows because CSV header "
                    "does not match current schema"
                )
        writer.writerows(rows)


def _git_commit_hash() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _git_dirty() -> bool | str:
    try:
        output = subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return bool(output.strip())
    except Exception:
        return "unknown"


def _cpu_model() -> str:
    processor = platform.processor().strip()
    if processor:
        return processor
    if platform.system().lower() == "windows":
        try:
            output = subprocess.check_output(
                ["wmic", "cpu", "get", "Name"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            names = [line.strip() for line in output.splitlines() if line.strip() and line.strip() != "Name"]
            if names:
                return names[0]
        except Exception:
            pass
    return "unknown"


def _total_ram_bytes() -> int | str:
    try:
        import psutil  # type: ignore

        return int(psutil.virtual_memory().total)
    except Exception:
        return "unknown"


def _physical_cores() -> int | str:
    try:
        import psutil  # type: ignore

        cores = psutil.cpu_count(logical=False)
        return int(cores) if cores is not None else "unknown"
    except Exception:
        return "unknown"


def write_hardware_profile(path: Path) -> None:
    """Write reproducibility metadata for CPU-only benchmark runs."""
    env_keys = ("GF2_L1D_BYTES", "GF2_L2_BYTES", "GF2_L3_BYTES", "GF2_CACHE_LINE_BYTES")
    profile = {
        "cpu_model": _cpu_model(),
        "logical_cores": os.cpu_count() or "unknown",
        "physical_cores": _physical_cores(),
        "ram_bytes": _total_ram_bytes(),
        "os": platform.platform(),
        "python_version": sys.version.replace("\n", " "),
        "numpy_version": np.__version__,
        "commit_hash": _git_commit_hash(),
        "git_dirty": _git_dirty(),
        "cache_profile_env_vars": {key: os.environ.get(key, "") for key in env_keys},
        "selected_cache_profiles": list(LIGHTWEIGHT_CACHE_PROFILES),
        "gpu_used": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")


def get_selection_cache_profile(name: str) -> CacheProfile:
    """Return one named cache profile for selection experiments."""
    if name == "default_cpu_cache":
        return get_cache_profile(
            profile_name=name,
            notes="default CPU cache profile for selection benchmark",
        )
    if name == "small_l2_profile":
        return get_cache_profile(
            profile_name=name,
            l1d_bytes=32 * 1024,
            l2_bytes=128 * 1024,
            l3_bytes=2 * 1024 * 1024,
            cache_line_bytes=64,
            notes="small L2 profile for cache-sensitive LUT selection",
        )
    if name == "large_l3_profile":
        return get_cache_profile(
            profile_name=name,
            l1d_bytes=48 * 1024,
            l2_bytes=2 * 1024 * 1024,
            l3_bytes=64 * 1024 * 1024,
            cache_line_bytes=64,
            notes="large L3 profile for cache-sensitive LUT selection",
        )
    raise ValueError("unknown cache profile")


def _packed_word_bits(r: int) -> int:
    return 16 if r <= 16 else 32


def _pack_batch(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _mean_us(samples: list[float]) -> float:
    return statistics.fmean(samples) * 1_000_000.0


def _outputs_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict):
        return (
            np.array_equal(actual["corrected_words"], expected["corrected_words"])
            and np.array_equal(actual["correction_masks"], expected["correction_masks"])
            and np.array_equal(actual["statuses"], expected["statuses"])
        )
    return bool(np.array_equal(actual, expected))


def _make_sparse_word(rng: np.random.Generator, n: int, weight: int) -> np.ndarray:
    x = np.zeros(n, dtype=np.uint8)
    x[rng.choice(n, size=min(weight, n), replace=False)] = 1
    return x


def _make_flip_positions(
    rng: np.random.Generator,
    batch_size: int,
    n: int,
    flip_count: int,
) -> np.ndarray:
    return np.stack(
        [rng.choice(n, size=flip_count, replace=False) for _ in range(batch_size)],
        axis=0,
    ).astype(np.int64, copy=False)


def _apply_flips(x_batch: np.ndarray, flip_positions: np.ndarray) -> np.ndarray:
    flipped = x_batch.copy()
    rows = np.repeat(np.arange(x_batch.shape[0]), flip_positions.shape[1])
    cols = flip_positions.reshape(-1)
    flipped[rows, cols] ^= 1
    return flipped


def _candidate_specs(
    *,
    matrix: np.ndarray,
    workload_type: str,
    batch_size: int,
    block_widths: tuple[int, ...],
    rng: np.random.Generator,
) -> tuple[str, str, dict[str, Any], list[dict[str, Any]], Any]:
    n, r = matrix.shape
    packed_bits = _packed_word_bits(r)
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_luts = {
        width: PackedBlockLUTKernel(matrix, block_width=width, packed_word_bits=packed_bits)
        for width in block_widths
    }
    specs: list[dict[str, Any]] = []

    if workload_type == "sparse_single":
        weight = 2
        x = _make_sparse_word(rng, n, weight)
        expected = naive.apply(x)
        sparse = SparseXorKernel(matrix)
        specs.extend(
            [
                {"backend": "NaiveGF2Kernel", "block_width": 0, "fn": lambda: naive.apply(x)},
                {"backend": "SparseXorKernel", "block_width": 0, "fn": lambda: sparse.apply(x)},
            ]
        )
        for width, kernel in packed_luts.items():
            specs.append(
                {
                    "backend": "PackedBlockLUTKernel",
                    "block_width": width,
                    "fn": lambda kernel=kernel: kernel.apply(x),
                }
            )
        workload = {
            "type": "sparse_single",
            "batch_size": 1,
            "hamming_weight": weight,
            "output_mode": "unpacked",
        }
        return "weight=2", "unpacked", workload, specs, expected

    if workload_type == "event_update":
        density = 0.05
        flip_count = 2
        x_batch = make_batch(rng, batch_size, density, n=n)
        old = naive.apply_many(x_batch)
        flips = _make_flip_positions(rng, batch_size, n, flip_count)
        flipped = _apply_flips(x_batch, flips)
        expected = naive.apply_many(flipped)
        event_kernel = EventUpdateKernel(matrix)
        specs.extend(
            [
                {
                    "backend": "NaiveGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: naive.apply_many(flipped),
                },
                {
                    "backend": "PackedBatchGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: packed_batch.apply_many(flipped),
                },
                {
                    "backend": "EventUpdateKernel",
                    "block_width": 0,
                    "fn": lambda: event_kernel.update_many(old, flips),
                },
            ]
        )
        for width, kernel in packed_luts.items():
            specs.append(
                {
                    "backend": "PackedBlockLUTKernel",
                    "block_width": width,
                    "fn": lambda kernel=kernel: kernel.apply_many(flipped),
                }
            )
        workload = {
            "type": "event_update",
            "batch_size": batch_size,
            "flip_count": flip_count,
            "output_mode": "unpacked",
        }
        return "flip_count=2", "unpacked", workload, specs, expected

    density = 0.5 if workload_type == "dense_batch" else 0.05
    if workload_type == "component_decode_batch":
        density = 0.02
    x_batch = make_batch(rng, batch_size, density, n=n)

    if workload_type == "candidate_test_packed":
        expected_unpacked = naive.apply_many(x_batch)
        expected = _pack_batch(expected_unpacked)
        specs.extend(
            [
                {
                    "backend": "NaiveGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: _pack_batch(naive.apply_many(x_batch)),
                },
                {
                    "backend": "PackedBatchGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: _pack_batch(packed_batch.apply_many(x_batch)),
                },
            ]
        )
        for width, kernel in packed_luts.items():
            specs.append(
                {
                    "backend": "PackedBlockLUTKernel",
                    "block_width": width,
                    "fn": lambda kernel=kernel: kernel.apply_many_packed(x_batch),
                }
            )
        workload = {
            "type": "candidate_test_packed",
            "batch_size": batch_size,
            "candidate_count": batch_size,
            "density": density,
            "output_mode": "packed",
        }
        return f"density={density}", "packed", workload, specs, expected

    if workload_type == "component_decode_batch":
        decoder = BDDLUTDecoder(matrix, t=2, strict_collision_check=False)
        expected = decoder.decode_words(x_batch, syndrome_backend=naive)
        specs.extend(
            [
                {
                    "backend": "NaiveGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: decoder.decode_words(x_batch, syndrome_backend=naive),
                },
                {
                    "backend": "PackedBatchGF2Kernel",
                    "block_width": 0,
                    "fn": lambda: decoder.decode_words(x_batch, syndrome_backend=packed_batch),
                },
            ]
        )
        for width, kernel in packed_luts.items():
            specs.append(
                {
                    "backend": "PackedBlockLUTKernel",
                    "block_width": width,
                    "fn": lambda kernel=kernel: decoder.decode_words(
                        x_batch,
                        syndrome_backend=kernel,
                    ),
                }
            )
        workload = {
            "type": "component_decode_batch",
            "batch_size": batch_size,
            "density": density,
            "output_mode": "unpacked",
        }
        return f"density={density}", "unpacked", workload, specs, expected

    expected = naive.apply_many(x_batch)
    specs.extend(
        [
            {"backend": "NaiveGF2Kernel", "block_width": 0, "fn": lambda: naive.apply_many(x_batch)},
            {
                "backend": "PackedBatchGF2Kernel",
                "block_width": 0,
                "fn": lambda: packed_batch.apply_many(x_batch),
            },
        ]
    )
    for width, kernel in packed_luts.items():
        specs.append(
            {
                "backend": "PackedBlockLUTKernel",
                "block_width": width,
                "fn": lambda kernel=kernel: kernel.apply_many(x_batch),
            }
        )
    workload = {
        "type": "dense_batch",
        "batch_size": batch_size,
        "density": density,
        "output_mode": "unpacked",
    }
    return f"density={density}", "unpacked", workload, specs, expected


def _evaluate_case(
    *,
    preset: str,
    profile_name: str,
    cache_profile: CacheProfile,
    workload_type: str,
    batch_size: int,
    block_widths: tuple[int, ...],
    repeats: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    profile = get_code_profile(profile_name)
    matrix = get_profile_matrix(profile_name)
    n, r = matrix.shape
    density_or_weight, output_mode, workload, specs, expected = _candidate_specs(
        matrix=matrix,
        workload_type=workload_type,
        batch_size=batch_size,
        block_widths=block_widths,
        rng=rng,
    )
    planner = CacheAwarePlanner(
        matrix,
        cache_profile=cache_profile,
        block_width_candidates=block_widths,
    )
    selection = planner.select(workload)
    timed: list[dict[str, Any]] = []
    for spec in specs:
        actual = spec["fn"]()
        if not _outputs_equal(actual, expected):
            raise AssertionError(
                f"cache-aware selection correctness failed: {profile.profile_name},"
                f"{cache_profile.profile_name},{workload_type},{spec['backend']}"
            )
        samples = time_repeats(spec["fn"], repeats=repeats, warmups=1)
        timed.append({**spec, "latency_us": _mean_us(samples)})

    selected_candidates = [
        row
        for row in timed
        if row["backend"] == selection.selected_backend
        and int(row["block_width"]) == int(selection.selected_block_width)
    ]
    if not selected_candidates:
        selected_candidates = [row for row in timed if row["backend"] == selection.selected_backend]
    if not selected_candidates:
        raise AssertionError(f"selected backend was not benchmarked: {selection.selected_backend}")
    selected_row = min(selected_candidates, key=lambda row: float(row["latency_us"]))
    oracle_row = min(timed, key=lambda row: float(row["latency_us"]))
    selected_latency = float(selected_row["latency_us"])
    oracle_latency = float(oracle_row["latency_us"])
    planner_over_oracle = selected_latency / oracle_latency if oracle_latency > 0 else math.nan
    return {
        "preset": preset,
        "code_profile": profile.profile_name,
        "n": n,
        "r": r,
        "cache_profile": cache_profile.profile_name,
        "workload_type": workload_type,
        "batch_size": int(workload.get("batch_size", batch_size)),
        "density_or_weight": density_or_weight,
        "output_mode": output_mode,
        "selected_backend": selection.selected_backend,
        "selected_block_width": selection.selected_block_width,
        "selection_reason": selection.selection_reason,
        "lut_bytes": selection.lut_bytes,
        "fits_l1": selection.fits_l1,
        "fits_l2": selection.fits_l2,
        "fits_l3": selection.fits_l3,
        "uses_lut": selection.uses_lut,
        "cache_fit_applicable": selection.cache_fit_applicable,
        "oracle_best_backend": oracle_row["backend"],
        "oracle_best_block_width": oracle_row["block_width"],
        "selected_latency_us": selected_latency,
        "oracle_best_latency_us": oracle_latency,
        "planner_over_oracle": planner_over_oracle,
        "correctness_passed": True,
    }


def run_cache_aware_selection_rows(
    *,
    preset: str,
    code_profiles: tuple[str, ...],
    cache_profiles: tuple[str, ...],
    workload_types: tuple[str, ...],
    batch_sizes: tuple[int, ...],
    block_width_candidates: tuple[int, ...],
    repeats: int,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(RNG_SEED)
    rows: list[dict[str, Any]] = []
    for profile_name in code_profiles:
        for cache_name in cache_profiles:
            cache_profile = get_selection_cache_profile(cache_name)
            for workload_type in workload_types:
                effective_batch_sizes = (1,) if workload_type == "sparse_single" else batch_sizes
                for batch_size in effective_batch_sizes:
                    rows.append(
                        _evaluate_case(
                            preset=preset,
                            profile_name=profile_name,
                            cache_profile=cache_profile,
                            workload_type=workload_type,
                            batch_size=batch_size,
                            block_widths=block_width_candidates,
                            repeats=repeats,
                            rng=rng,
                        )
                    )
    return [{field: row.get(field, "") for field in CACHE_AWARE_SELECTION_FIELDNAMES} for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run cache-aware selection benchmark.")
    parser.add_argument(
        "--preset",
        choices=("lightweight", "paper", "paper-small", "full"),
        default="lightweight",
    )
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--cache-profiles", default=None)
    parser.add_argument("--workload-types", default=None)
    parser.add_argument("--batch-sizes", default=None)
    parser.add_argument("--block-widths", default=None)
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preset = args.preset
    defaults = _preset_defaults(preset)
    repeats = args.repeats if args.repeats is not None else defaults["repeats"]
    code_profiles = _parse_str_list(args.code_profiles) if args.code_profiles else defaults["code_profiles"]
    cache_profiles = (
        _parse_str_list(args.cache_profiles) if args.cache_profiles else defaults["cache_profiles"]
    )
    workload_types = (
        _parse_str_list(args.workload_types) if args.workload_types else defaults["workload_types"]
    )
    batch_sizes = _parse_int_list(args.batch_sizes) if args.batch_sizes else defaults["batch_sizes"]
    block_widths = (
        _parse_int_list(args.block_widths) if args.block_widths else defaults["block_widths"]
    )

    ensure_result_dirs()
    rows = run_cache_aware_selection_rows(
        preset=preset,
        code_profiles=code_profiles,
        cache_profiles=cache_profiles,
        workload_types=workload_types,
        batch_sizes=batch_sizes,
        block_width_candidates=block_widths,
        repeats=repeats,
    )
    output = RAW_DIR / "cache_aware_selection.csv"
    _write_or_append_csv(output, rows, append=args.append)
    write_hardware_profile(RAW_DIR / "hardware_profile.json")
    verb = "appended" if args.append and output.exists() else "wrote"
    print(f"{verb} {output}")
    print(f"wrote {RAW_DIR / 'hardware_profile.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
