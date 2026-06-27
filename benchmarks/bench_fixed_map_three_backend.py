"""Three-backend fixed GF(2) map benchmark for parity and syndrome tasks."""

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
from codes.bch_like import make_bch255_t2_syndrome_matrix_galois_systematic
from linear_kernel import NaiveGF2Kernel, PackedBatchGF2Kernel, PackedBlockLUTKernel
from linear_kernel.cache_profile import get_cache_profile
from linear_kernel.matrix_utils import pack_batch_bits_to_uint16, pack_batch_bits_to_uint32

DEFAULT_BATCH_SIZES = (1, 10, 100, 1_000, 10_000, 100_000, 1_000_000)
DEFAULT_LONG_BATCH_SIZES = (5_000_000,)
DEFAULT_REPEATS = 9
DEFAULT_WARMUPS = 2
DEFAULT_BLOCK_WIDTH = 12
DEFAULT_MAX_IN_MEMORY_ROWS = 100_000
DEFAULT_MAX_GALOIS_BATCH_SIZE = 10_000
DEFAULT_MAX_TIMED_BATCH_SIZE = 1_000_000
RNG_SEED = 20260729

FIELDNAMES = [
    "profile",
    "task",
    "backend",
    "baseline_role",
    "batch_size",
    "input_width",
    "output_width",
    "processed_bits",
    "block_width",
    "packed_word_bits",
    "chunked_online",
    "chunk_size",
    "build_init_s",
    "exactness_elapsed_s",
    "timing_elapsed_s",
    "elapsed_s",
    "median_runtime_s",
    "min_runtime_s",
    "max_runtime_s",
    "cv",
    "throughput_Mbit_s",
    "throughput_Mcodeword_s",
    "samples_s",
    "warmups",
    "repeats",
    "correctness_passed",
    "timed",
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
    """A systematic BCH matrix profile for fixed-map benchmarks."""

    profile: str
    matrix: np.ndarray
    k: int
    init_elapsed_s: float
    bch: Any | None = None


@dataclass(frozen=True)
class BackendSpec:
    backend: str
    baseline_role: str
    output_mode: str
    fn: Callable[[np.ndarray], np.ndarray]
    notes: str
    max_batch_size: int | None = None


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
    return rng.integers(0, 2, size=(int(batch_size), int(width)), dtype=np.uint8)


def pack_batch(bits: np.ndarray) -> np.ndarray:
    if bits.shape[1] <= 16:
        return pack_batch_bits_to_uint16(bits)
    return pack_batch_bits_to_uint32(bits)


def _summary(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {
            "median_runtime_s": 0.0,
            "min_runtime_s": 0.0,
            "max_runtime_s": 0.0,
            "cv": 0.0,
        }
    mean = statistics.fmean(samples)
    std = statistics.stdev(samples) if len(samples) > 1 else 0.0
    return {
        "median_runtime_s": statistics.median(samples),
        "min_runtime_s": min(samples),
        "max_runtime_s": max(samples),
        "cv": (std / mean) if mean > 0 else 0.0,
    }


def _time_samples(fn: Callable[[], np.ndarray], *, warmups: int, repeats: int) -> list[float]:
    for _ in range(warmups):
        fn()
    samples: list[float] = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)
    return samples


def _cpu_model() -> str:
    for value in (platform.processor(), platform.uname().processor, os.environ.get("PROCESSOR_IDENTIFIER", "")):
        if value:
            return str(value)
    return "unknown"


def _galois_version() -> tuple[bool, str]:
    try:
        import galois
    except ImportError:
        return False, ""
    return True, str(getattr(galois, "__version__", "unknown"))


def environment_fields() -> dict[str, Any]:
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


def build_systematic_bch_matrix(n: int, k: int, profile: str | None = None) -> MatrixSpec:
    """Build ``H^T=[P;I]`` from one systematic ``galois.BCH(n,k)`` instance."""

    try:
        import galois
    except ImportError as exc:
        raise RuntimeError("galois is required to build systematic BCH matrices") from exc

    start = time.perf_counter()
    bch = galois.BCH(int(n), int(k))
    r = int(n) - int(k)
    parity_rows = []
    basis = np.zeros(int(k), dtype=np.int32)
    for position in range(int(k)):
        basis.fill(0)
        basis[position] = 1
        codeword = np.asarray(bch.encode(basis), dtype=np.int32)
        parity_rows.append((codeword[int(k) :] & 1).astype(np.uint8, copy=False))
    parity_matrix = np.stack(parity_rows, axis=0).astype(np.uint8, copy=False)
    matrix = np.concatenate([parity_matrix, np.eye(r, dtype=np.uint8)], axis=0)
    elapsed = time.perf_counter() - start
    name = profile or f"bch_{int(n)}_{int(k)}_r{r}"
    return MatrixSpec(name, matrix.astype(np.uint8, copy=False), int(k), elapsed, bch=bch)


def default_matrix_specs() -> tuple[MatrixSpec, ...]:
    start = time.perf_counter()
    matrix = make_bch255_t2_syndrome_matrix_galois_systematic()
    bch255_elapsed = time.perf_counter() - start
    try:
        import galois

        bch255 = galois.BCH(255, 239)
    except ImportError:
        bch255 = None
    return (
        MatrixSpec("bch_255_239_r16", matrix, 239, bch255_elapsed, bch=bch255),
        build_systematic_bch_matrix(511, 484),
    )


def _galois_matrix_apply_per_codeword(x_batch: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    import galois

    gf2 = galois.GF(2)
    gf_matrix = gf2(matrix)
    rows = [np.asarray(gf2(row.reshape(1, -1)) @ gf_matrix, dtype=np.uint8).reshape(-1) for row in x_batch]
    return np.stack(rows, axis=0).astype(np.uint8, copy=False) if rows else np.zeros((0, matrix.shape[1]), dtype=np.uint8)


def _galois_encode_parity_per_codeword(x_batch: np.ndarray, spec: MatrixSpec) -> np.ndarray:
    if spec.bch is None:
        return _galois_matrix_apply_per_codeword(x_batch, spec.matrix[: spec.k])
    rows = [np.asarray(spec.bch.encode(np.asarray(row, dtype=np.int32)), dtype=np.int32)[spec.k :] & 1 for row in x_batch]
    return np.stack(rows, axis=0).astype(np.uint8, copy=False) if rows else np.zeros((0, spec.matrix.shape[1]), dtype=np.uint8)


def _make_backend_specs(
    *,
    spec: MatrixSpec,
    task: str,
    matrix: np.ndarray,
    block_width: int,
    include_galois: bool,
    max_galois_batch_size: int,
) -> list[BackendSpec]:
    packed_word_bits = 16 if matrix.shape[1] <= 16 else 32
    packed_batch = PackedBatchGF2Kernel(matrix)
    packed_lut = PackedBlockLUTKernel(matrix, block_width=block_width, packed_word_bits=packed_word_bits)
    backends = [
        BackendSpec(
            "PackedBatchGF2Kernel.apply_many",
            "fair vectorized same-task baseline",
            "unpacked",
            packed_batch.apply_many,
            "headline fair baseline for fixed xA",
        ),
        BackendSpec(
            "PackedBlockLUTKernel.apply_many_packed",
            "packed block-LUT kernel under test",
            "packed",
            packed_lut.apply_many_packed,
            "block width selected from cache sweep",
        ),
    ]
    if include_galois:
        if task == "parity":
            fn = lambda x, spec=spec: _galois_encode_parity_per_codeword(x, spec)
            notes = "naive library-call baseline, per-codeword bch.encode"
        else:
            fn = lambda x, matrix=matrix: _galois_matrix_apply_per_codeword(x, matrix)
            notes = "naive library-call baseline, per-codeword galois GF(2) matmul"
        backends.insert(
            0,
            BackendSpec(
                "galois_per_codeword",
                "naive library-call baseline, per-codeword",
                "unpacked",
                fn,
                notes,
                max_batch_size=max_galois_batch_size,
            ),
        )
    return backends


def _make_stream_fn(fn: Callable[[np.ndarray], np.ndarray], chunks: tuple[np.ndarray, ...]) -> Callable[[], np.ndarray]:
    def apply_stream() -> np.ndarray:
        last = np.array([], dtype=np.uint8)
        for chunk in chunks:
            last = fn(chunk)
        return last

    return apply_stream


def _make_chunks(
    *,
    input_width: int,
    batch_size: int,
    max_in_memory_rows: int,
    rng: np.random.Generator,
) -> tuple[tuple[np.ndarray, ...], bool, int]:
    chunk_size = max(1, min(int(batch_size), int(max_in_memory_rows)))
    chunks = []
    remaining = int(batch_size)
    while remaining > 0:
        current = min(chunk_size, remaining)
        chunks.append(_random_batch(input_width, current, rng))
        remaining -= current
    return tuple(chunks), len(chunks) > 1, chunk_size


def _row_for_backend(
    *,
    spec: MatrixSpec,
    task: str,
    backend: BackendSpec,
    matrix: np.ndarray,
    batch_size: int,
    block_width: int,
    warmups: int,
    repeats: int,
    max_in_memory_rows: int,
    max_timed_batch_size: int | None,
    rng: np.random.Generator,
    env: dict[str, Any],
    seed: int,
) -> dict[str, Any]:
    config_start = time.perf_counter()
    input_width, output_width = matrix.shape
    chunks, chunked, chunk_size = _make_chunks(
        input_width=input_width,
        batch_size=batch_size,
        max_in_memory_rows=max_in_memory_rows,
        rng=rng,
    )
    exact_start = time.perf_counter()
    reference = NaiveGF2Kernel(matrix).apply_many(chunks[0])
    expected = pack_batch(reference) if backend.output_mode == "packed" else reference
    actual = backend.fn(chunks[0])
    correctness_passed = bool(np.array_equal(actual, expected))
    exact_elapsed = time.perf_counter() - exact_start
    samples: list[float] = []
    timing_elapsed = 0.0
    timed = False
    notes = backend.notes
    over_general_limit = max_timed_batch_size is not None and batch_size > max_timed_batch_size
    over_backend_limit = backend.max_batch_size is not None and batch_size > backend.max_batch_size
    if correctness_passed and not over_general_limit and not over_backend_limit:
        stream_fn = _make_stream_fn(backend.fn, chunks)
        timing_start = time.perf_counter()
        samples = _time_samples(stream_fn, warmups=warmups, repeats=repeats)
        timing_elapsed = time.perf_counter() - timing_start
        timed = True
    elif correctness_passed:
        if over_general_limit:
            notes = f"{notes}; skipped timing above max_timed_batch_size={max_timed_batch_size}"
        if over_backend_limit:
            notes = f"{notes}; skipped timing above backend max_batch_size={backend.max_batch_size}"
    summary = _summary(samples)
    median = summary["median_runtime_s"]
    processed_bits = int(batch_size) * int(input_width)
    elapsed = time.perf_counter() - config_start
    return {
        "profile": spec.profile,
        "task": task,
        "backend": backend.backend,
        "baseline_role": backend.baseline_role,
        "batch_size": int(batch_size),
        "input_width": int(input_width),
        "output_width": int(output_width),
        "processed_bits": processed_bits,
        "block_width": int(block_width) if backend.backend == "PackedBlockLUTKernel.apply_many_packed" else "",
        "packed_word_bits": 16 if output_width <= 16 else 32,
        "chunked_online": chunked,
        "chunk_size": int(chunk_size),
        "build_init_s": float(spec.init_elapsed_s),
        "exactness_elapsed_s": exact_elapsed,
        "timing_elapsed_s": timing_elapsed,
        "elapsed_s": elapsed,
        **summary,
        "throughput_Mbit_s": processed_bits / median / 1_000_000.0 if median > 0 else 0.0,
        "throughput_Mcodeword_s": int(batch_size) / median / 1_000_000.0 if median > 0 else 0.0,
        "samples_s": ";".join(f"{sample:.12g}" for sample in samples),
        "warmups": int(warmups),
        "repeats": int(repeats),
        "correctness_passed": correctness_passed,
        "timed": timed,
        **env,
        "seed": int(seed),
        "notes": notes,
    }


def run_three_backend_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    batch_sizes: tuple[int, ...] = DEFAULT_BATCH_SIZES,
    long_batch_sizes: tuple[int, ...] = DEFAULT_LONG_BATCH_SIZES,
    repeats: int = DEFAULT_REPEATS,
    warmups: int = DEFAULT_WARMUPS,
    block_widths_by_task: dict[tuple[str, str], int] | None = None,
    default_block_width: int = DEFAULT_BLOCK_WIDTH,
    include_galois: bool = True,
    max_in_memory_rows: int = DEFAULT_MAX_IN_MEMORY_ROWS,
    max_timed_batch_size: int | None = DEFAULT_MAX_TIMED_BATCH_SIZE,
    max_galois_batch_size: int = DEFAULT_MAX_GALOIS_BATCH_SIZE,
    seed: int = RNG_SEED,
) -> list[dict[str, Any]]:
    """Return rows for parity and syndrome fixed-map backend comparisons."""

    _force_single_thread_env()
    env = environment_fields()
    include_galois = bool(include_galois and env["galois_available"])
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for raw_spec in matrix_specs or default_matrix_specs():
        matrix = _as_gf2_matrix(raw_spec.matrix)
        spec = MatrixSpec(raw_spec.profile, matrix, int(raw_spec.k), float(raw_spec.init_elapsed_s), raw_spec.bch)
        task_matrices = (("parity", matrix[: spec.k]), ("syndrome", matrix))
        for task, task_matrix in task_matrices:
            block_width = int((block_widths_by_task or {}).get((spec.profile, task), default_block_width))
            for batch_size in tuple(batch_sizes) + tuple(long_batch_sizes):
                for backend in _make_backend_specs(
                    spec=spec,
                    task=task,
                    matrix=task_matrix,
                    block_width=block_width,
                    include_galois=include_galois,
                    max_galois_batch_size=max_galois_batch_size,
                ):
                    rows.append(
                        _row_for_backend(
                            spec=spec,
                            task=task,
                            backend=backend,
                            matrix=task_matrix,
                            batch_size=int(batch_size),
                            block_width=block_width,
                            warmups=warmups,
                            repeats=repeats,
                            max_in_memory_rows=max_in_memory_rows,
                            max_timed_batch_size=max_timed_batch_size,
                            rng=rng,
                            env=env,
                            seed=seed,
                        )
                    )
    return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def load_block_widths_from_sweep(path: Path, selection_batch_size: int) -> dict[tuple[str, str], int]:
    if not path.exists():
        return {}
    best: dict[tuple[str, str], tuple[float, int]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("backend") != "PackedBlockLUTKernel.apply_many_packed":
                continue
            if int(row.get("batch_size", 0)) != int(selection_batch_size):
                continue
            if row.get("correctness_passed") != "True" or row.get("timed") != "True":
                continue
            key = (row["profile"], row["task"])
            throughput = float(row["throughput_Mbit_s"])
            block_width = int(row["block_width"])
            if key not in best or throughput > best[key][0]:
                best[key] = (throughput, block_width)
    return {key: value[1] for key, value in best.items()}


def _write_or_append_csv(output: Path, rows: list[dict[str, Any]], append: bool) -> None:
    if append and output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            rows = [*list(csv.DictReader(f)), *rows]
    write_csv(output, rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run three-backend fixed GF(2) map benchmark.")
    parser.add_argument("--batch-sizes", default=",".join(str(value) for value in DEFAULT_BATCH_SIZES))
    parser.add_argument("--long-batch-sizes", default=",".join(str(value) for value in DEFAULT_LONG_BATCH_SIZES))
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--warmups", type=int, default=DEFAULT_WARMUPS)
    parser.add_argument("--default-block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--block-width-source", type=Path, default=RAW_DIR / "block_width_cache_sweep.csv")
    parser.add_argument("--selection-batch-size", type=int, default=100_000)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--max-timed-batch-size", type=int, default=DEFAULT_MAX_TIMED_BATCH_SIZE)
    parser.add_argument("--max-galois-batch-size", type=int, default=DEFAULT_MAX_GALOIS_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--skip-galois", action="store_true")
    parser.add_argument("--output", type=Path, default=RAW_DIR / "fixed_map_three_backend.csv")
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    widths = load_block_widths_from_sweep(args.block_width_source, args.selection_batch_size)
    rows = run_three_backend_rows(
        batch_sizes=_parse_int_list(args.batch_sizes),
        long_batch_sizes=_parse_int_list(args.long_batch_sizes),
        repeats=args.repeats,
        warmups=args.warmups,
        block_widths_by_task=widths,
        default_block_width=args.default_block_width,
        include_galois=not args.skip_galois,
        max_in_memory_rows=args.max_in_memory_rows,
        max_timed_batch_size=args.max_timed_batch_size,
        max_galois_batch_size=args.max_galois_batch_size,
        seed=args.seed,
    )
    _write_or_append_csv(args.output, rows, args.append)
    print(f"wrote {args.output}")
    failed = [row for row in rows if row["correctness_passed"] is not True]
    if failed:
        print(f"WARNING: {len(failed)} rows failed exactness and were not timed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
