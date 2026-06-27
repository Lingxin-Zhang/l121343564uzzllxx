"""Fair same-task GF(2) throughput benchmark with absolute rates."""

from __future__ import annotations

import argparse
import csv
import os
import platform
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

for _THREAD_ENV_NAME in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ[_THREAD_ENV_NAME] = "1"

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, write_csv
from codes.code_profiles import get_profile_matrix
from codes.matrix_sources import get_matrix_source
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.cache_profile import get_cache_profile
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

DEFAULT_BATCH_SIZES = (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000)
DEFAULT_REPEATS = 5
DEFAULT_WARMUPS = 1
DEFAULT_BLOCK_WIDTH = 8
RNG_SEED = 20260728

FIELDNAMES = [
    "profile",
    "task",
    "backend",
    "baseline_role",
    "output_mode",
    "batch_size",
    "input_width",
    "output_width",
    "processed_bits",
    "median_runtime_s",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "samples_s",
    "warmups",
    "repeats",
    "block_width",
    "packed_word_bits",
    "correctness_passed",
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


@dataclass(frozen=True)
class MatrixSpec:
    """One profile used for the fair throughput benchmark."""

    profile: str
    matrix: np.ndarray
    k: int


@dataclass(frozen=True)
class TimedBackend:
    """One timed backend call."""

    backend: str
    baseline_role: str
    output_mode: str
    fn: Callable[[], np.ndarray]
    expected: np.ndarray
    notes: str


def default_matrix_specs() -> tuple[MatrixSpec, ...]:
    """Return the required BCH and eBCH candidate matrices."""

    return (
        MatrixSpec(
            "bch_255_239_r16",
            get_matrix_source("galois_systematic_candidate"),
            k=239,
        ),
        MatrixSpec(
            "ebch_256_239_r17",
            get_profile_matrix("ebch_256_239_r17"),
            k=239,
        ),
    )


def _force_single_thread_env() -> None:
    for name in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[name] = "1"


def _as_gf2_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.uint8) & 1
    if matrix.ndim != 2:
        raise ValueError("matrix must be 2-D")
    return matrix


def _random_batch(width: int, batch_size: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, 2, size=(batch_size, width), dtype=np.uint8)


def _pack_batch(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _galois_version() -> tuple[bool, str]:
    try:
        import galois
    except ImportError:
        return False, ""
    return True, str(getattr(galois, "__version__", "unknown"))


def _galois_apply_many(x_batch: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    import galois

    gf2 = galois.GF(2)
    return np.asarray(gf2(x_batch) @ gf2(matrix), dtype=np.uint8)


def _time_samples(fn: Callable[[], np.ndarray], *, warmups: int, repeats: int) -> list[float]:
    for _ in range(warmups):
        fn()
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _cpu_model() -> str:
    candidates = [
        platform.processor(),
        platform.uname().processor,
        os.environ.get("PROCESSOR_IDENTIFIER", ""),
    ]
    for value in candidates:
        if value:
            return str(value)
    return "unknown"


def _environment_fields() -> dict[str, Any]:
    cache = get_cache_profile()
    available, version = _galois_version()
    thread_values = [
        os.environ.get(name, "")
        for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        if os.environ.get(name)
    ]
    return {
        "galois_available": available,
        "galois_version": version,
        "cpu_model": _cpu_model(),
        "l1d_bytes": cache.l1d_bytes,
        "l2_bytes": cache.l2_bytes,
        "l3_bytes": cache.l3_bytes,
        "python_version": sys.version.split()[0],
        "numpy_version": np.__version__,
        "thread_count": ";".join(thread_values) or "1",
    }


def _make_timed_backends(
    *,
    matrix: np.ndarray,
    x_batch: np.ndarray,
    include_galois: bool,
    block_width: int,
) -> list[TimedBackend]:
    packed_word_bits = 16 if matrix.shape[1] <= 16 else 32
    naive = NaiveGF2Kernel(matrix)
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(
        matrix,
        block_width=block_width,
        packed_word_bits=packed_word_bits,
    )
    fair_expected = packed_batch.apply_many(x_batch)
    packed_expected = _pack_batch(fair_expected)
    backends = [
        TimedBackend(
            "NaiveGF2Kernel.apply_many",
            "vectorization-overhead reference only",
            "unpacked",
            lambda naive=naive, x_batch=x_batch: naive.apply_many(x_batch),
            fair_expected,
            "not a headline baseline",
        ),
        TimedBackend(
            "PackedBatchGF2Kernel.apply_many",
            "fair vectorized baseline",
            "unpacked",
            lambda packed_batch=packed_batch, x_batch=x_batch: packed_batch.apply_many(x_batch),
            fair_expected,
            "same-task vectorized baseline",
        ),
    ]
    if include_galois:
        galois_output = _galois_apply_many(x_batch, matrix)
        if np.array_equal(galois_output, fair_expected):
            backends.append(
                TimedBackend(
                    "galois.GF2_matmul",
                    "third-party verified same-task baseline",
                    "unpacked",
                    lambda x_batch=x_batch, matrix=matrix: _galois_apply_many(x_batch, matrix),
                    fair_expected,
                    "galois output matched PackedBatchGF2Kernel before timing",
                )
            )
        else:
            backends.append(
                TimedBackend(
                    "galois.GF2_matmul",
                    "sanity check only; output mismatch",
                    "unpacked",
                    lambda galois_output=galois_output: galois_output,
                    fair_expected,
                    "galois output mismatch; throughput row records correctness_passed=False",
                )
            )
    backends.append(
        TimedBackend(
            "PackedBlockLUTKernel.apply_many_packed",
            "packed block-LUT kernel under test",
            "packed",
            lambda packed_lut=packed_lut, x_batch=x_batch: packed_lut.apply_many_packed(x_batch),
            packed_expected,
            "vectorized packed LUT path; not BlockLUTKernel.apply_many",
        )
    )
    return backends


def _result_row(
    *,
    spec: MatrixSpec,
    task: str,
    backend: TimedBackend,
    batch_size: int,
    input_width: int,
    output_width: int,
    block_width: int,
    warmups: int,
    repeats: int,
    seed: int,
    env: dict[str, Any],
) -> dict[str, Any]:
    actual = backend.fn()
    correctness_passed = bool(np.array_equal(actual, backend.expected))
    if not correctness_passed:
        samples: list[float] = []
        median = 0.0
    else:
        samples = _time_samples(backend.fn, warmups=warmups, repeats=repeats)
        median = statistics.median(samples)
    processed_bits = batch_size * input_width
    throughput_mbit = processed_bits / median / 1_000_000.0 if median > 0 else 0.0
    throughput_mcodeword = batch_size / median / 1_000_000.0 if median > 0 else 0.0
    return {
        "profile": spec.profile,
        "task": task,
        "backend": backend.backend,
        "baseline_role": backend.baseline_role,
        "output_mode": backend.output_mode,
        "batch_size": batch_size,
        "input_width": input_width,
        "output_width": output_width,
        "processed_bits": processed_bits,
        "median_runtime_s": median,
        "throughput_Mbit_s": throughput_mbit,
        "throughput_Mcodeword_s": throughput_mcodeword,
        "samples_s": ";".join(f"{sample:.12g}" for sample in samples),
        "warmups": warmups,
        "repeats": repeats,
        "block_width": block_width,
        "packed_word_bits": 16 if output_width <= 16 else 32,
        "correctness_passed": correctness_passed,
        **env,
        "seed": seed,
        "notes": backend.notes,
    }


def run_fair_baseline_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    block_width: int = DEFAULT_BLOCK_WIDTH,
    seed: int = RNG_SEED,
    include_galois: bool = True,
) -> list[dict[str, Any]]:
    """Return fair same-task throughput rows without writing files."""

    _force_single_thread_env()
    rng = np.random.default_rng(seed)
    env = _environment_fields()
    include_galois = bool(include_galois and env["galois_available"])
    rows: list[dict[str, Any]] = []
    for raw_spec in matrix_specs or default_matrix_specs():
        matrix = _as_gf2_matrix(raw_spec.matrix)
        spec = MatrixSpec(raw_spec.profile, matrix, int(raw_spec.k))
        if not 0 < spec.k <= matrix.shape[0]:
            raise ValueError(f"profile {spec.profile!r} has invalid k={spec.k}")
        task_matrices = (
            ("syndrome", matrix, matrix.shape[0]),
            ("parity", matrix[: spec.k], spec.k),
        )
        for task, task_matrix, input_width in task_matrices:
            output_width = task_matrix.shape[1]
            for batch_size in batch_sizes:
                x_batch = _random_batch(input_width, int(batch_size), rng)
                for backend in _make_timed_backends(
                    matrix=task_matrix,
                    x_batch=x_batch,
                    include_galois=include_galois,
                    block_width=block_width,
                ):
                    rows.append(
                        _result_row(
                            spec=spec,
                            task=task,
                            backend=backend,
                            batch_size=int(batch_size),
                            input_width=input_width,
                            output_width=output_width,
                            block_width=block_width,
                            warmups=warmups,
                            repeats=repeats,
                            seed=seed,
                            env=env,
                        )
                    )
    return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]


def _write_or_append_csv(output: Path, rows: list[dict[str, Any]], append: bool) -> None:
    if append and output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            rows = [*list(csv.DictReader(f)), *rows]
    write_csv(output, rows)


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run fair same-task GF(2) throughput benchmark.")
    parser.add_argument(
        "--batch-sizes",
        default=",".join(str(value) for value in DEFAULT_BATCH_SIZES),
    )
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--skip-galois", action="store_true")
    parser.add_argument("--output", type=Path, default=RAW_DIR / "fair_baseline_throughput.csv")
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_fair_baseline_rows(
        batch_sizes=_parse_int_list(args.batch_sizes),
        repeats=args.repeats,
        warmups=args.warmups,
        block_width=args.block_width,
        seed=args.seed,
        include_galois=not args.skip_galois,
    )
    _write_or_append_csv(args.output, rows, args.append)
    print(f"wrote {args.output}")
    failed = [row for row in rows if row["correctness_passed"] is not True]
    if failed:
        print(f"WARNING: {len(failed)} rows failed correctness and were not timed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
