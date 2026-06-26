"""Long-stream packed-LUT block-width/cache-level benchmark."""

from __future__ import annotations

import argparse
import csv
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, make_batch, write_csv
from codes.code_profiles import CodeProfile, get_code_profile, get_profile_matrix
from codes.matrix_sources import get_matrix_source
from linear_kernel import NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.cache_profile import estimate_block_lut_bytes, get_cache_profile
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

RNG_SEED = 20260809
DEFAULT_MATRIX_SOURCE = "galois_systematic_candidate"
DEFAULT_DENSITY = 0.05
DEFAULT_CHUNK_WORDS = 4096
DEFAULT_VERIFY_WORDS = 4096

LIGHTWEIGHT_TOTAL_BITS = (1_000_000, 10_000_000)
LIGHTWEIGHT_ITERATIONS = (1, 5)
LIGHTWEIGHT_BLOCK_WIDTHS = (6, 8, 10, 12)

PAPER_TOTAL_BITS = (10_000_000, 50_000_000, 200_000_000)
PAPER_ITERATIONS = (1, 5, 10)
PAPER_BLOCK_WIDTHS = (6, 8, 10, 12, 14, 16, 18, 20)

FULL_TOTAL_BITS = (10_000_000, 50_000_000, 200_000_000, 500_000_000)
FULL_ITERATIONS = (1, 5, 10)
FULL_BLOCK_WIDTHS = (4, 6, 8, 10, 12, 14, 16, 18, 20)

LONG_STREAM_CACHE_WIDTH_FIELDNAMES = [
    "preset",
    "code_profile",
    "matrix_kind",
    "verification_status",
    "matrix_source",
    "matrix_shape",
    "component_n",
    "output_r",
    "total_bits",
    "num_words",
    "chunk_words",
    "iterations",
    "density",
    "block_width",
    "packed_word_bits",
    "lut_bytes",
    "stream_input_bytes",
    "lut_over_l1",
    "lut_over_l2",
    "lut_over_l3",
    "num_blocks",
    "entries_per_block",
    "fits_l1",
    "fits_l2",
    "fits_l3",
    "cache_level",
    "l1d_bytes",
    "l2_bytes",
    "l3_bytes",
    "cache_line_bytes",
    "verification_words",
    "latency_per_word_us",
    "latency_per_word_std_us",
    "latency_cv",
    "throughput_Mword_s",
    "throughput_Mbit_s",
    "repeats",
    "mean",
    "std",
    "correctness_passed",
]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_str_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def cache_level_from_fit(fits_l1: bool, fits_l2: bool, fits_l3: bool) -> str:
    """Return the smallest cache level that can hold the LUT footprint."""

    if fits_l1:
        return "L1"
    if fits_l2:
        return "L2"
    if fits_l3:
        return "L3"
    return "memory"


def _packed_word_bits(r: int) -> int:
    return 16 if r <= 16 else 32


def _pack_expected(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _manual_matrix_profile(matrix_source: str, matrix: np.ndarray) -> CodeProfile:
    n, r = matrix.shape
    return CodeProfile(
        profile_name=matrix_source,
        n=n,
        r=r,
        matrix_source=matrix_source,
        matrix_kind="matrix_source",
        is_synthetic=False,
        verification_status="source_defined",
        notes="Manual matrix source passed through long-stream cache-width benchmark.",
    )


def _iter_chunks(x_words: np.ndarray, chunk_words: int):
    for start in range(0, x_words.shape[0], chunk_words):
        yield x_words[start : start + chunk_words]


def _run_stream(
    x_words: np.ndarray,
    *,
    chunk_words: int,
    iterations: int,
    fn: Callable[[np.ndarray], np.ndarray],
) -> None:
    for _ in range(iterations):
        for chunk in _iter_chunks(x_words, chunk_words):
            fn(chunk)


def _time_stream(
    x_words: np.ndarray,
    *,
    chunk_words: int,
    iterations: int,
    repeats: int,
    fn: Callable[[np.ndarray], np.ndarray],
) -> list[float]:
    _run_stream(x_words, chunk_words=chunk_words, iterations=1, fn=fn)
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        _run_stream(
            x_words,
            chunk_words=chunk_words,
            iterations=iterations,
            fn=fn,
        )
        samples.append(time.perf_counter() - start)
    return samples


def _verify_sample(
    x_words: np.ndarray,
    *,
    naive: NaiveGF2Kernel,
    packed_lut: PackedBlockLUTKernel,
    verify_words: int,
) -> tuple[bool, int]:
    words = min(max(1, int(verify_words)), x_words.shape[0])
    sample = x_words[:words]
    expected = _pack_expected(naive.apply_many(sample))
    actual = packed_lut.apply_many_packed(sample)
    if not np.array_equal(actual, expected):
        raise AssertionError("PackedBlockLUT.apply_many_packed disagrees with Naive sample")
    return True, words


def _summary(samples: list[float], processed_words: int) -> dict[str, float]:
    per_word = [sample / processed_words for sample in samples]
    mean = statistics.fmean(per_word)
    per_word_std = statistics.stdev(per_word) if len(per_word) > 1 else 0.0
    sample_std = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "latency_per_word_us": mean * 1_000_000.0,
        "latency_per_word_std_us": per_word_std * 1_000_000.0,
        "latency_cv": per_word_std / mean if mean > 0 else 0.0,
        "throughput_Mword_s": (1.0 / mean / 1_000_000.0) if mean > 0 else 0.0,
        "mean": statistics.fmean(samples),
        "std": sample_std,
    }


def _preset_defaults(preset: str) -> dict[str, Any]:
    if preset == "lightweight":
        return {
            "total_bits_values": LIGHTWEIGHT_TOTAL_BITS,
            "iterations_values": LIGHTWEIGHT_ITERATIONS,
            "block_widths": LIGHTWEIGHT_BLOCK_WIDTHS,
            "repeats": 3,
        }
    if preset == "paper":
        return {
            "total_bits_values": PAPER_TOTAL_BITS,
            "iterations_values": PAPER_ITERATIONS,
            "block_widths": PAPER_BLOCK_WIDTHS,
            "repeats": 5,
        }
    if preset == "full":
        return {
            "total_bits_values": FULL_TOTAL_BITS,
            "iterations_values": FULL_ITERATIONS,
            "block_widths": FULL_BLOCK_WIDTHS,
            "repeats": 7,
        }
    raise ValueError(f"unknown preset: {preset}")


def run_long_stream_cache_width_rows(
    *,
    preset: str,
    matrix_source: str | None = None,
    code_profiles: tuple[str, ...] | None = None,
    total_bits_values: tuple[int, ...],
    iterations_values: tuple[int, ...],
    block_widths: tuple[int, ...],
    density: float,
    chunk_words: int,
    repeats: int,
    verify_words: int = DEFAULT_VERIFY_WORDS,
    l1d_bytes: int | None = None,
    l2_bytes: int | None = None,
    l3_bytes: int | None = None,
    cache_line_bytes: int | None = None,
) -> list[dict[str, Any]]:
    cache_profile = get_cache_profile(
        profile_name="cli_override"
        if any(value is not None for value in (l1d_bytes, l2_bytes, l3_bytes, cache_line_bytes))
        else "generic_desktop",
        l1d_bytes=l1d_bytes,
        l2_bytes=l2_bytes,
        l3_bytes=l3_bytes,
        cache_line_bytes=cache_line_bytes,
    )
    rows: list[dict[str, Any]] = []

    profile_names = tuple(code_profiles or ())
    if profile_names:
        profile_matrix_pairs = [
            (get_code_profile(profile_name), get_profile_matrix(profile_name))
            for profile_name in profile_names
        ]
    else:
        source = matrix_source or DEFAULT_MATRIX_SOURCE
        matrix = get_matrix_source(source)
        profile_matrix_pairs = [(_manual_matrix_profile(source, matrix), matrix)]

    for profile, matrix in profile_matrix_pairs:
        component_n, output_r = matrix.shape
        packed_bits = _packed_word_bits(output_r)
        naive = NaiveGF2Kernel(matrix)
        rng = np.random.default_rng(RNG_SEED + component_n + output_r)

        for total_bits in total_bits_values:
            num_words = max(1, int(total_bits) // component_n)
            stream_input_bytes = int(num_words * component_n)
            x_words = make_batch(rng, num_words, density, n=component_n)
            for block_width in block_widths:
                lut_info = estimate_block_lut_bytes(
                    n=component_n,
                    r=output_r,
                    block_width=block_width,
                    packed_word_bits=packed_bits,
                    cache_profile=cache_profile,
                )
                lut_bytes = int(lut_info["lut_bytes"])
                packed_lut = PackedBlockLUTKernel(
                    matrix,
                    block_width=block_width,
                    packed_word_bits=packed_bits,
                )
                correctness_passed, verification_words = _verify_sample(
                    x_words,
                    naive=naive,
                    packed_lut=packed_lut,
                    verify_words=verify_words,
                )
                fn = packed_lut.apply_many_packed
                for iterations in iterations_values:
                    processed_words = num_words * int(iterations)
                    samples = _time_stream(
                        x_words,
                        chunk_words=chunk_words,
                        iterations=int(iterations),
                        repeats=repeats,
                        fn=fn,
                    )
                    summary = _summary(samples, processed_words)
                    rows.append(
                        {
                            "preset": preset,
                            "code_profile": profile.profile_name,
                            "matrix_kind": profile.matrix_kind,
                            "verification_status": profile.verification_status,
                            "matrix_source": profile.matrix_source,
                            "matrix_shape": f"{component_n}x{output_r}",
                            "component_n": component_n,
                            "output_r": output_r,
                            "total_bits": int(total_bits),
                            "num_words": num_words,
                            "chunk_words": chunk_words,
                            "iterations": int(iterations),
                            "density": density,
                            "block_width": int(block_width),
                            "packed_word_bits": packed_bits,
                            "lut_bytes": lut_bytes,
                            "stream_input_bytes": stream_input_bytes,
                            "lut_over_l1": lut_bytes / cache_profile.l1d_bytes,
                            "lut_over_l2": lut_bytes / cache_profile.l2_bytes,
                            "lut_over_l3": lut_bytes / cache_profile.l3_bytes,
                            "num_blocks": int(lut_info["num_blocks"]),
                            "entries_per_block": int(lut_info["entries_per_block"]),
                            "fits_l1": bool(lut_info["fits_l1"]),
                            "fits_l2": bool(lut_info["fits_l2"]),
                            "fits_l3": bool(lut_info["fits_l3"]),
                            "cache_level": cache_level_from_fit(
                                bool(lut_info["fits_l1"]),
                                bool(lut_info["fits_l2"]),
                                bool(lut_info["fits_l3"]),
                            ),
                            "l1d_bytes": cache_profile.l1d_bytes,
                            "l2_bytes": cache_profile.l2_bytes,
                            "l3_bytes": cache_profile.l3_bytes,
                            "cache_line_bytes": cache_profile.cache_line_bytes,
                            "verification_words": verification_words,
                            "throughput_Mbit_s": summary["throughput_Mword_s"] * component_n,
                            **summary,
                            "repeats": repeats,
                            "correctness_passed": correctness_passed,
                        }
                    )
    return [{field: row.get(field, "") for field in LONG_STREAM_CACHE_WIDTH_FIELDNAMES} for row in rows]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run long-stream PackedBlockLUT block-width/cache-level sweep."
    )
    parser.add_argument("--preset", choices=("lightweight", "paper", "full"), default="lightweight")
    parser.add_argument("--matrix-source", default=DEFAULT_MATRIX_SOURCE)
    parser.add_argument("--code-profiles", default=None)
    parser.add_argument("--total-bits", default=None)
    parser.add_argument("--iterations", default=None)
    parser.add_argument("--block-widths", default=None)
    parser.add_argument("--density", type=float, default=DEFAULT_DENSITY)
    parser.add_argument("--chunk-words", type=int, default=DEFAULT_CHUNK_WORDS)
    parser.add_argument("--verify-words", type=int, default=DEFAULT_VERIFY_WORDS)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--l1d-kb", type=int, default=None)
    parser.add_argument("--l2-kb", type=int, default=None)
    parser.add_argument("--l3-mb", type=int, default=None)
    parser.add_argument("--cache-line", type=int, default=None)
    parser.add_argument(
        "--output",
        type=Path,
        default=RAW_DIR / "long_stream_cache_width.csv",
        help="Output CSV path. Defaults to results/raw/long_stream_cache_width.csv.",
    )
    parser.add_argument("--append", action="store_true")
    return parser


def _write_or_append_csv(path, rows: list[dict[str, Any]], *, append: bool) -> None:
    if not append:
        write_csv(path, rows)
        return
    if not rows:
        raise ValueError(f"no benchmark rows to write: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if path.exists() else "w"
    with path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if mode == "w":
            writer.writeheader()
        else:
            with path.open(newline="", encoding="utf-8") as existing:
                existing_header = next(csv.reader(existing), [])
            if existing_header != list(rows[0].keys()):
                raise ValueError("cannot append rows because existing CSV header differs")
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    defaults = _preset_defaults(args.preset)
    total_bits_values = (
        _parse_int_list(args.total_bits) if args.total_bits else defaults["total_bits_values"]
    )
    iterations_values = (
        _parse_int_list(args.iterations) if args.iterations else defaults["iterations_values"]
    )
    block_widths = (
        _parse_int_list(args.block_widths) if args.block_widths else defaults["block_widths"]
    )
    repeats = int(args.repeats if args.repeats is not None else defaults["repeats"])

    ensure_result_dirs()
    rows = run_long_stream_cache_width_rows(
        preset=args.preset,
        matrix_source=args.matrix_source,
        code_profiles=_parse_str_list(args.code_profiles) if args.code_profiles else None,
        total_bits_values=total_bits_values,
        iterations_values=iterations_values,
        block_widths=block_widths,
        density=args.density,
        chunk_words=args.chunk_words,
        repeats=repeats,
        verify_words=args.verify_words,
        l1d_bytes=args.l1d_kb * 1024 if args.l1d_kb is not None else None,
        l2_bytes=args.l2_kb * 1024 if args.l2_kb is not None else None,
        l3_bytes=args.l3_mb * 1024 * 1024 if args.l3_mb is not None else None,
        cache_line_bytes=args.cache_line,
    )
    output = args.output
    _write_or_append_csv(output, rows, append=args.append)
    print(f"{'appended' if args.append else 'wrote'} {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
