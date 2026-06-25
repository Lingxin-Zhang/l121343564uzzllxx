"""Cache-aware packed-LUT benchmark across code profiles."""

from __future__ import annotations

import argparse
import statistics
from collections.abc import Callable
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from linear_kernel import (
    NaiveGF2Kernel,
    PackedBatchGF2Kernel,
    PackedBlockLUTKernel,
    SparseXorKernel,
)
from linear_kernel.cache_profile import CacheProfile, estimate_block_lut_bytes, get_cache_profile
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

from ._common import RAW_DIR, ensure_result_dirs, make_batch, time_repeats, write_csv

LIGHTWEIGHT_BLOCK_WIDTHS = (4, 6, 8, 10, 12, 14, 16, 18, 20)
LIGHTWEIGHT_BATCH_SIZES = (1, 64, 4096)
LIGHTWEIGHT_DENSITIES = (0.005, 0.05, 0.5)
LIGHTWEIGHT_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_511_r32",
)
FULL_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_bch_like_127_r14",
    "synthetic_511_r32",
)
FULL_BATCH_SIZES = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FULL_DENSITIES = (0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5)

RNG_SEED = 20260720

CACHE_AWARE_FIELDNAMES = [
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
    "packed_word_bits",
    "packed_dtype",
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
    "latency_per_word_us",
    "throughput_Mword_s",
    "mean",
    "std",
    "repeats",
    "correctness_passed",
]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _packed_word_bits(r: int) -> int:
    return 16 if r <= 16 else 32


def _pack_expected(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def assert_correct(
    backend: str,
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    context: str,
) -> None:
    """Raise immediately when a benchmark backend disagrees with the oracle."""

    if not np.array_equal(actual, expected):
        raise AssertionError(f"cache-aware correctness failed for {backend}: {context}")


def _summary(samples: list[float], batch_size: int) -> dict[str, float]:
    per_word = [sample / batch_size for sample in samples]
    mean = statistics.fmean(per_word)
    std = statistics.stdev(per_word) if len(per_word) > 1 else 0.0
    return {
        "latency_per_word_us": mean * 1_000_000.0,
        "throughput_Mword_s": (1.0 / mean / 1_000_000.0) if mean > 0 else 0.0,
        "mean": mean,
        "std": std,
    }


def _timed_row(
    *,
    preset: str,
    code_profile: str,
    n: int,
    r: int,
    backend: str,
    block_width: int,
    batch_size: int,
    density: float,
    packed_word_bits: int,
    packed_dtype: str,
    cache_profile: CacheProfile,
    lut_info: dict[str, Any],
    samples: list[float],
    repeats: int,
) -> dict[str, Any]:
    summary = _summary(samples, batch_size)
    return {
        "preset": preset,
        "cache_profile": cache_profile.profile_name,
        "code_profile": code_profile,
        "matrix_shape": f"{n}x{r}",
        "n": n,
        "r": r,
        "backend": backend,
        "block_width": block_width,
        "batch_size": batch_size,
        "density": density,
        "packed_word_bits": packed_word_bits,
        "packed_dtype": packed_dtype,
        "lut_bytes": lut_info["lut_bytes"],
        "num_blocks": lut_info["num_blocks"],
        "entries_per_block": lut_info["entries_per_block"],
        "fits_l1": lut_info["fits_l1"],
        "fits_l2": lut_info["fits_l2"],
        "fits_l3": lut_info["fits_l3"],
        "l1d_bytes": cache_profile.l1d_bytes,
        "l2_bytes": cache_profile.l2_bytes,
        "l3_bytes": cache_profile.l3_bytes,
        "cache_line_bytes": cache_profile.cache_line_bytes,
        **summary,
        "repeats": repeats,
        "correctness_passed": True,
    }


def _time_backend(
    fn: Callable[[], Any],
    repeats: int,
) -> list[float]:
    return time_repeats(fn, repeats=repeats, warmups=1)


def _run_for_profile(
    *,
    preset: str,
    profile_name: str,
    block_widths: tuple[int, ...],
    batch_sizes: tuple[int, ...],
    densities: tuple[float, ...],
    repeats: int,
    cache_profile: CacheProfile,
) -> list[dict[str, Any]]:
    profile = get_code_profile(profile_name)
    matrix = get_profile_matrix(profile_name)
    n, r = matrix.shape
    packed_bits = _packed_word_bits(r)
    packed_dtype = "uint16" if packed_bits == 16 else "uint32"
    naive = NaiveGF2Kernel(matrix)
    sparse = SparseXorKernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(RNG_SEED + n + r)

    zero_lut = {
        "lut_bytes": 0,
        "num_blocks": 0,
        "entries_per_block": 0,
        "fits_l1": True,
        "fits_l2": True,
        "fits_l3": True,
    }
    for density in densities:
        for batch_size in batch_sizes:
            x_batch = make_batch(rng, batch_size, density, n=n)
            expected = naive.apply_many(x_batch)
            baseline_specs = [
                ("Naive.apply_many", lambda: naive.apply_many(x_batch), expected),
                ("SparseXor.apply_many", lambda: sparse.apply_many(x_batch), expected),
                ("PackedBatch.apply_many", lambda: packed_batch.apply_many(x_batch), expected),
            ]
            baseline_results = []
            for backend, fn, expected_unpacked in baseline_specs:
                actual = fn()
                assert_correct(
                    backend,
                    actual,
                    expected_unpacked,
                    context=f"{profile.profile_name},batch={batch_size},density={density}",
                )
                samples = _time_backend(fn, repeats)
                baseline_results.append((backend, samples))
            for block_width in block_widths:
                for backend, samples in baseline_results:
                    rows.append(
                        _timed_row(
                            preset=preset,
                            code_profile=profile.profile_name,
                            n=n,
                            r=r,
                            backend=backend,
                            block_width=block_width,
                            batch_size=batch_size,
                            density=density,
                            packed_word_bits=packed_bits,
                            packed_dtype=packed_dtype,
                            cache_profile=cache_profile,
                            lut_info=zero_lut,
                            samples=samples,
                            repeats=repeats,
                        )
                    )

                lut_info = estimate_block_lut_bytes(
                    n=n,
                    r=r,
                    block_width=block_width,
                    packed_word_bits=packed_bits,
                    cache_profile=cache_profile,
                )
                packed_lut = PackedBlockLUTKernel(
                    matrix,
                    block_width=block_width,
                    packed_word_bits=packed_bits,
                )
                expected_packed = _pack_expected(expected)
                fn = lambda packed_lut=packed_lut, x_batch=x_batch: packed_lut.apply_many_packed(x_batch)
                actual_packed = fn()
                assert_correct(
                    "PackedBlockLUT.apply_many_packed",
                    actual_packed,
                    expected_packed,
                    context=f"{profile.profile_name},block_width={block_width},batch={batch_size},density={density}",
                )
                samples = _time_backend(fn, repeats)
                rows.append(
                    _timed_row(
                        preset=preset,
                        code_profile=profile.profile_name,
                        n=n,
                        r=r,
                        backend="PackedBlockLUT.apply_many_packed",
                        block_width=block_width,
                        batch_size=batch_size,
                        density=density,
                        packed_word_bits=packed_bits,
                        packed_dtype=packed_dtype,
                        cache_profile=cache_profile,
                        lut_info=lut_info,
                        samples=samples,
                        repeats=repeats,
                    )
                )
    return rows


def run_cache_aware_rows(
    *,
    preset: str,
    code_profiles: tuple[str, ...],
    block_widths: tuple[int, ...],
    batch_sizes: tuple[int, ...],
    densities: tuple[float, ...],
    repeats: int,
    l1d_bytes: int | None = None,
    l2_bytes: int | None = None,
    l3_bytes: int | None = None,
    cache_line_bytes: int | None = None,
) -> list[dict[str, Any]]:
    profile_name = (
        "cli_override"
        if any(value is not None for value in (l1d_bytes, l2_bytes, l3_bytes, cache_line_bytes))
        else "generic_desktop"
    )
    cache_profile = get_cache_profile(
        profile_name=profile_name,
        l1d_bytes=l1d_bytes,
        l2_bytes=l2_bytes,
        l3_bytes=l3_bytes,
        cache_line_bytes=cache_line_bytes,
    )
    rows: list[dict[str, Any]] = []
    for profile_name in code_profiles:
        rows.extend(
            _run_for_profile(
                preset=preset,
                profile_name=profile_name,
                block_widths=block_widths,
                batch_sizes=batch_sizes,
                densities=densities,
                repeats=repeats,
                cache_profile=cache_profile,
            )
        )
    return [{field: row.get(field, "") for field in CACHE_AWARE_FIELDNAMES} for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run cache-aware GF(2) benchmark.")
    parser.add_argument("--preset", choices=("lightweight", "full"), default="lightweight")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--block-widths", default=None)
    parser.add_argument("--batch-sizes", default=None)
    parser.add_argument("--densities", default=None)
    parser.add_argument("--l1d-kb", type=int, default=None)
    parser.add_argument("--l2-kb", type=int, default=None)
    parser.add_argument("--l3-mb", type=int, default=None)
    parser.add_argument("--cache-line", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preset = args.preset
    repeats = args.repeats if args.repeats is not None else (3 if preset == "lightweight" else 7)
    code_profiles = (
        _parse_str_list(args.code_profiles)
        if args.code_profiles
        else (LIGHTWEIGHT_CODE_PROFILES if preset == "lightweight" else FULL_CODE_PROFILES)
    )
    block_widths = (
        _parse_int_list(args.block_widths)
        if args.block_widths
        else LIGHTWEIGHT_BLOCK_WIDTHS
    )
    batch_sizes = (
        _parse_int_list(args.batch_sizes)
        if args.batch_sizes
        else (LIGHTWEIGHT_BATCH_SIZES if preset == "lightweight" else FULL_BATCH_SIZES)
    )
    densities = (
        _parse_float_list(args.densities)
        if args.densities
        else (LIGHTWEIGHT_DENSITIES if preset == "lightweight" else FULL_DENSITIES)
    )

    ensure_result_dirs()
    rows = run_cache_aware_rows(
        preset=preset,
        code_profiles=code_profiles,
        block_widths=block_widths,
        batch_sizes=batch_sizes,
        densities=densities,
        repeats=repeats,
        l1d_bytes=args.l1d_kb * 1024 if args.l1d_kb is not None else None,
        l2_bytes=args.l2_kb * 1024 if args.l2_kb is not None else None,
        l3_bytes=args.l3_mb * 1024 * 1024 if args.l3_mb is not None else None,
        cache_line_bytes=args.cache_line,
    )
    output = RAW_DIR / "cache_aware.csv"
    write_csv(output, rows)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
