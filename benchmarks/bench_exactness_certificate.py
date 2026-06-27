"""Bit-exact certificate for GF(2) parity and syndrome kernels.

This benchmark is a correctness gate. It writes mismatch counts for each check
and exits non-zero if any tested backend differs from the NumPy reference.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np

from benchmarks._common import RAW_DIR, ensure_result_dirs, write_csv
from codes.code_profiles import get_profile_matrix
from codes.matrix_sources import get_matrix_source
from decoders.bdd_lut import BDDLUTDecoder
from linear_kernel import BlockLUTKernel, NaiveGF2Kernel, PackedBlockLUTKernel
from linear_kernel.matrix_utils import (
    pack_batch_bits_to_uint16,
    pack_batch_bits_to_uint32,
    unpack_uint16_to_bits,
    unpack_uint32_to_bits,
)

ANSI_RED = "\033[31m"
ANSI_RESET = "\033[0m"
DEFAULT_RANDOM_BATCH_SIZE = 65536
DEFAULT_DECODER_RANDOM_WORDS = 4096
DEFAULT_BLOCK_WIDTH = 8
RNG_SEED = 20260727

FIELDNAMES = [
    "profile",
    "check_name",
    "operation",
    "coverage",
    "comparator",
    "reference_backend",
    "tested_backend",
    "input_width",
    "output_width",
    "num_inputs",
    "mismatch_count",
    "status",
    "notes",
]


@dataclass(frozen=True)
class MatrixSpec:
    """One matrix/profile checked by the exactness certificate."""

    profile: str
    matrix: np.ndarray
    k: int


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


def _as_gf2_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.uint8) & 1
    if matrix.ndim != 2:
        raise ValueError("matrix must be 2-D")
    return matrix


def _single_bit_batch(width: int) -> np.ndarray:
    return np.eye(width, dtype=np.uint8)


def _double_bit_batch(width: int) -> np.ndarray:
    rows = np.zeros((width * (width - 1) // 2, width), dtype=np.uint8)
    for row, (left, right) in enumerate(combinations(range(width), 2)):
        rows[row, left] = 1
        rows[row, right] = 1
    return rows


def _random_batch(width: int, count: int, density: float, rng: np.random.Generator) -> np.ndarray:
    return (rng.random((count, width)) < density).astype(np.uint8)


def _unpack_packed_batch(packed: np.ndarray, output_width: int) -> np.ndarray:
    unpack = unpack_uint16_to_bits if output_width <= 16 else unpack_uint32_to_bits
    return np.stack([unpack(value, output_width) for value in packed], axis=0).astype(
        np.uint8,
        copy=False,
    )


def _make_backends(matrix: np.ndarray, block_width: int) -> tuple[NaiveGF2Kernel, list[tuple[str, Any]]]:
    reference = NaiveGF2Kernel(matrix)
    return reference, [
        ("BlockLUTKernel.apply_many", BlockLUTKernel(matrix, block_width=block_width)),
        (
            "PackedBlockLUTKernel.apply_many_packed",
            PackedBlockLUTKernel(matrix, block_width=block_width),
        ),
    ]


def _backend_apply_unpacked(backend_name: str, backend: Any, x_batch: np.ndarray, r: int) -> np.ndarray:
    if backend_name == "PackedBlockLUTKernel.apply_many_packed":
        return _unpack_packed_batch(backend.apply_many_packed(x_batch), r)
    return backend.apply_many(x_batch)


def _mismatch_count(expected: np.ndarray, actual: np.ndarray) -> int:
    if expected.shape != actual.shape:
        return max(expected.shape[0], actual.shape[0])
    if expected.ndim == 1:
        return int(np.count_nonzero(expected != actual))
    return int(np.count_nonzero(np.any(expected != actual, axis=1)))


def _row(
    *,
    spec: MatrixSpec,
    check_name: str,
    operation: str,
    coverage: str,
    tested_backend: str,
    input_width: int,
    output_width: int,
    num_inputs: int,
    mismatch_count: int,
    notes: str = "",
) -> dict[str, Any]:
    return {
        "profile": spec.profile,
        "check_name": check_name,
        "operation": operation,
        "coverage": coverage,
        "comparator": "bit_exact_equal",
        "reference_backend": "NaiveGF2Kernel.apply_many",
        "tested_backend": tested_backend,
        "input_width": input_width,
        "output_width": output_width,
        "num_inputs": num_inputs,
        "mismatch_count": mismatch_count,
        "status": "PASS" if mismatch_count == 0 else "FAIL",
        "notes": notes,
    }


def _kernel_rows_for_input_set(
    *,
    spec: MatrixSpec,
    matrix: np.ndarray,
    x_batch: np.ndarray,
    check_name: str,
    operation: str,
    coverage: str,
    block_width: int,
) -> list[dict[str, Any]]:
    reference, backends = _make_backends(matrix, block_width)
    expected = reference.apply_many(x_batch)
    rows = []
    _, r = matrix.shape
    for backend_name, backend in backends:
        actual = _backend_apply_unpacked(backend_name, backend, x_batch, r)
        rows.append(
            _row(
                spec=spec,
                check_name=check_name,
                operation=operation,
                coverage=coverage,
                tested_backend=backend_name,
                input_width=matrix.shape[0],
                output_width=r,
                num_inputs=x_batch.shape[0],
                mismatch_count=_mismatch_count(expected, actual),
            )
        )
    return rows


def _decoder_consistency_rows(
    *,
    spec: MatrixSpec,
    matrix: np.ndarray,
    words: np.ndarray,
    block_width: int,
) -> list[dict[str, Any]]:
    decoder = BDDLUTDecoder(matrix, t=2)
    reference_backend = NaiveGF2Kernel(matrix)
    expected = decoder.decode_words(words, syndrome_backend=reference_backend)
    backends = [
        ("BlockLUTKernel.apply_many", BlockLUTKernel(matrix, block_width=block_width)),
        (
            "PackedBlockLUTKernel.apply_many_packed",
            PackedBlockLUTKernel(matrix, block_width=block_width),
        ),
    ]
    rows = []
    n, r = matrix.shape
    for backend_name, backend in backends:
        actual = decoder.decode_words(words, syndrome_backend=backend)
        mask_mismatches = _mismatch_count(expected["correction_masks"], actual["correction_masks"])
        status_mismatches = int(np.count_nonzero(expected["statuses"] != actual["statuses"]))
        rows.append(
            _row(
                spec=spec,
                check_name="bdd_decoder_consistency",
                operation="component_bdd_lut_decode",
                coverage="random_received_words",
                tested_backend=backend_name,
                input_width=n,
                output_width=r,
                num_inputs=words.shape[0],
                mismatch_count=mask_mismatches + status_mismatches,
                notes=(
                    f"correction_mask_mismatches={mask_mismatches}; "
                    f"status_mismatches={status_mismatches}"
                ),
            )
        )
    return rows


def run_exactness_certificate_rows(
    *,
    matrix_specs: tuple[MatrixSpec, ...] | None = None,
    random_batch_size: int = DEFAULT_RANDOM_BATCH_SIZE,
    decoder_random_words: int = DEFAULT_DECODER_RANDOM_WORDS,
    random_density: float = 0.05,
    block_width: int = DEFAULT_BLOCK_WIDTH,
    seed: int = RNG_SEED,
) -> list[dict[str, Any]]:
    """Return exactness certificate rows without writing files."""

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for raw_spec in matrix_specs or default_matrix_specs():
        matrix = _as_gf2_matrix(raw_spec.matrix)
        spec = MatrixSpec(raw_spec.profile, matrix, int(raw_spec.k))
        n, _ = matrix.shape
        if not 0 < spec.k <= n:
            raise ValueError(f"profile {spec.profile!r} has invalid k={spec.k} for n={n}")
        parity_matrix = matrix[: spec.k]

        rows.extend(
            _kernel_rows_for_input_set(
                spec=spec,
                matrix=parity_matrix,
                x_batch=_single_bit_batch(spec.k),
                check_name="parity_single_bit",
                operation="parity",
                coverage="all_single_bit_messages",
                block_width=block_width,
            )
        )
        rows.extend(
            _kernel_rows_for_input_set(
                spec=spec,
                matrix=parity_matrix,
                x_batch=_random_batch(spec.k, random_batch_size, random_density, rng),
                check_name="parity_random_batch",
                operation="parity",
                coverage=f"random_batch_size={random_batch_size};density={random_density}",
                block_width=block_width,
            )
        )
        rows.extend(
            _kernel_rows_for_input_set(
                spec=spec,
                matrix=matrix,
                x_batch=_single_bit_batch(n),
                check_name="syndrome_single_bit",
                operation="syndrome",
                coverage="all_single_bit_words",
                block_width=block_width,
            )
        )
        rows.extend(
            _kernel_rows_for_input_set(
                spec=spec,
                matrix=matrix,
                x_batch=_double_bit_batch(n),
                check_name="syndrome_double_bit",
                operation="syndrome",
                coverage="all_double_bit_words",
                block_width=block_width,
            )
        )
        rows.extend(
            _kernel_rows_for_input_set(
                spec=spec,
                matrix=matrix,
                x_batch=_random_batch(n, random_batch_size, random_density, rng),
                check_name="syndrome_random_batch",
                operation="syndrome",
                coverage=f"random_batch_size={random_batch_size};density={random_density}",
                block_width=block_width,
            )
        )
        rows.extend(
            _decoder_consistency_rows(
                spec=spec,
                matrix=matrix,
                words=_random_batch(n, decoder_random_words, random_density, rng),
                block_width=block_width,
            )
        )
    return [{field: row.get(field, "") for field in FIELDNAMES} for row in rows]


def _write_or_append_csv(output: Path, rows: list[dict[str, Any]], append: bool) -> None:
    if append and output.exists():
        with output.open(newline="", encoding="utf-8") as f:
            rows = [*list(csv.DictReader(f)), *rows]
    write_csv(output, rows)


def _raise_if_mismatches(rows: list[dict[str, Any]]) -> None:
    failing = [row for row in rows if int(row["mismatch_count"]) != 0]
    if not failing:
        print("exactness certificate PASS: all mismatch_count values are 0")
        return
    print(f"{ANSI_RED}EXACTNESS CERTIFICATE FAILED: {len(failing)} rows have mismatches{ANSI_RESET}")
    for row in failing:
        print(
            f"{ANSI_RED}{row['profile']} {row['check_name']} {row['tested_backend']} "
            f"mismatch_count={row['mismatch_count']}{ANSI_RESET}"
        )
    raise SystemExit(1)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run bit-exact GF(2) kernel certificate.")
    parser.add_argument("--random-batch-size", type=int, default=DEFAULT_RANDOM_BATCH_SIZE)
    parser.add_argument("--decoder-random-words", type=int, default=DEFAULT_DECODER_RANDOM_WORDS)
    parser.add_argument("--random-density", type=float, default=0.05)
    parser.add_argument("--block-width", type=int, default=DEFAULT_BLOCK_WIDTH)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--output", type=Path, default=RAW_DIR / "exactness_certificate.csv")
    parser.add_argument("--append", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_exactness_certificate_rows(
        random_batch_size=args.random_batch_size,
        decoder_random_words=args.decoder_random_words,
        random_density=args.random_density,
        block_width=args.block_width,
        seed=args.seed,
    )
    _write_or_append_csv(args.output, rows, args.append)
    print(f"wrote {args.output}")
    _raise_if_mismatches(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
