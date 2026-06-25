"""Code-profile scaling benchmark for GF(2) backends."""

from __future__ import annotations

import argparse
import statistics
from typing import Any

import numpy as np

from codes.code_profiles import get_code_profile, get_profile_matrix
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel, SparseXorKernel
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

from ._common import RAW_DIR, ensure_result_dirs, make_batch, time_repeats, write_csv

LIGHTWEIGHT_CODE_PROFILES = (
    "bch_255_239_r16",
    "ebch_256_239_r17",
    "synthetic_bch_like_127_r14",
    "synthetic_511_r32",
)
LIGHTWEIGHT_BATCH_SIZES = (1, 64, 4096)
LIGHTWEIGHT_DENSITIES = (0.05,)
FULL_BATCH_SIZES = (1, 4, 16, 64, 256, 1024, 4096, 16384)
FULL_DENSITIES = (0.005, 0.05, 0.5)
RNG_SEED = 20260721


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


def _row(
    *,
    preset: str,
    code_profile: str,
    n: int,
    r: int,
    backend: str,
    batch_size: int,
    density: float,
    block_width: int,
    packed_word_bits: int,
    samples: list[float],
    repeats: int,
    correctness_passed: bool,
) -> dict[str, Any]:
    return {
        "preset": preset,
        "code_profile": code_profile,
        "n": n,
        "r": r,
        "backend": backend,
        "batch_size": batch_size,
        "density": density,
        "block_width": block_width,
        "packed_word_bits": packed_word_bits,
        **_summary(samples, batch_size),
        "repeats": repeats,
        "correctness_passed": correctness_passed,
    }


def _run_profile(
    *,
    preset: str,
    profile_name: str,
    batch_sizes: tuple[int, ...],
    densities: tuple[float, ...],
    block_width: int,
    repeats: int,
) -> list[dict[str, Any]]:
    profile = get_code_profile(profile_name)
    matrix = get_profile_matrix(profile_name)
    n, r = matrix.shape
    packed_bits = _packed_word_bits(r)
    naive = NaiveGF2Kernel(matrix)
    sparse = SparseXorKernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(
        matrix,
        block_width=block_width,
        packed_word_bits=packed_bits,
    )
    rng = np.random.default_rng(RNG_SEED + n + r)
    rows: list[dict[str, Any]] = []
    for density in densities:
        for batch_size in batch_sizes:
            x_batch = make_batch(rng, batch_size, density, n=n)
            expected = naive.apply_many(x_batch)
            expected_packed = _pack_expected(expected)
            specs = [
                ("Naive.apply_many", lambda: naive.apply_many(x_batch), expected),
                ("SparseXor.apply_many", lambda: sparse.apply_many(x_batch), expected),
                ("PackedBatch.apply_many", lambda: packed_batch.apply_many(x_batch), expected),
                (
                    "PackedBlockLUT.apply_many_packed",
                    lambda: packed_lut.apply_many_packed(x_batch),
                    expected_packed,
                ),
            ]
            for backend, fn, expected_value in specs:
                actual = fn()
                correctness = bool(np.array_equal(actual, expected_value))
                samples = time_repeats(fn, repeats=repeats, warmups=1)
                rows.append(
                    _row(
                        preset=preset,
                        code_profile=profile.profile_name,
                        n=n,
                        r=r,
                        backend=backend,
                        batch_size=batch_size,
                        density=density,
                        block_width=block_width,
                        packed_word_bits=packed_bits,
                        samples=samples,
                        repeats=repeats,
                        correctness_passed=correctness,
                    )
                )
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run code-profile scaling benchmark.")
    parser.add_argument("--preset", choices=("lightweight", "full"), default="lightweight")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--batch-sizes", default=None)
    parser.add_argument("--densities", default=None)
    parser.add_argument("--block-width", type=int, default=8)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    preset = args.preset
    repeats = args.repeats if args.repeats is not None else (3 if preset == "lightweight" else 7)
    code_profiles = (
        _parse_str_list(args.code_profiles)
        if args.code_profiles
        else LIGHTWEIGHT_CODE_PROFILES
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
    rows: list[dict[str, Any]] = []
    for profile_name in code_profiles:
        rows.extend(
            _run_profile(
                preset=preset,
                profile_name=profile_name,
                batch_sizes=batch_sizes,
                densities=densities,
                block_width=args.block_width,
                repeats=repeats,
            )
        )
    output = RAW_DIR / "code_profile_scaling.csv"
    write_csv(output, rows)
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
