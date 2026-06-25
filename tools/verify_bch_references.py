"""Triangulate BCH-like syndrome matrices against optional references.

The script is intentionally local-friendly: unavailable external references are
reported in CSV output instead of causing a crash. External code may be invoked
as behavior reference, but no external implementation code is copied here.
"""

from __future__ import annotations

import argparse
import csv
import importlib
import importlib.metadata
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codes.bch_like import make_bch255_t2_syndrome_matrix  # noqa: E402

DEFAULT_OUTPUT = ROOT / "results" / "raw" / "bch_reference_check.csv"
DEFAULT_REFERENCES = ("ofec", "galois", "python-bchlib", "aff3ct", "linux-kernel")
N_BCH = 255
K_BCH = 239
R_BCH = N_BCH - K_BCH


@dataclass(frozen=True)
class ComparisonRow:
    reference_name: str
    reference_available: bool
    reference_type: str
    parameters: str
    candidate_transform: str
    shape: str
    num_equal_entries: int
    num_total_entries: int
    match_rate: float
    exact_match: bool
    notes: str


@dataclass(frozen=True)
class ReferenceMatrix:
    name: str
    reference_type: str
    parameters: str
    matrix: np.ndarray
    notes: str


def _as_gf2_matrix(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.uint8) & 1
    if matrix.ndim != 2:
        raise ValueError("reference matrix must be 2-D")
    return matrix


def _packed_uint16_to_bits(values: np.ndarray, width: int = R_BCH) -> np.ndarray:
    values = np.asarray(values, dtype=np.uint16).reshape(-1)
    shifts = np.arange(width, dtype=np.uint16)
    return ((values[:, None] >> shifts) & np.uint16(1)).astype(np.uint8)


def reverse_codeword_positions(matrix: np.ndarray) -> np.ndarray:
    return _as_gf2_matrix(matrix)[::-1]


def reverse_bit_order_inside_each_byte(matrix: np.ndarray) -> np.ndarray:
    matrix = _as_gf2_matrix(matrix)
    if matrix.shape[1] % 8 != 0:
        return matrix
    reshaped = matrix.reshape(matrix.shape[0], matrix.shape[1] // 8, 8)
    return reshaped[:, :, ::-1].reshape(matrix.shape)


def reverse_output_byte_order(matrix: np.ndarray) -> np.ndarray:
    matrix = _as_gf2_matrix(matrix)
    if matrix.shape[1] % 8 != 0:
        return matrix
    reshaped = matrix.reshape(matrix.shape[0], matrix.shape[1] // 8, 8)
    return reshaped[:, ::-1, :].reshape(matrix.shape)


def reverse_output_bit_order(matrix: np.ndarray) -> np.ndarray:
    return _as_gf2_matrix(matrix)[:, ::-1]


def _candidate_row_variants(matrix: np.ndarray) -> list[tuple[str, np.ndarray]]:
    variants = [("all_rows", matrix)]
    if matrix.shape[0] == N_BCH + 1:
        variants.append(("drop_last_ebch_parity_row", matrix[:-1]))
        variants.append(("drop_first_row", matrix[1:]))
    return variants


def _transform_functions() -> list[tuple[str, Callable[[np.ndarray], np.ndarray]]]:
    return [
        ("identity", lambda x: _as_gf2_matrix(x)),
        ("reverse_codeword_positions", reverse_codeword_positions),
        ("reverse_bit_order_inside_each_byte", reverse_bit_order_inside_each_byte),
        ("reverse_output_byte_order", reverse_output_byte_order),
        ("reverse_output_bit_order", reverse_output_bit_order),
    ]


def _compare_arrays(candidate: np.ndarray, ours: np.ndarray) -> tuple[int, int, float, bool]:
    if candidate.shape != ours.shape:
        total = int(max(candidate.size, ours.size))
        return 0, total, 0.0, False
    equal = int(np.count_nonzero(candidate == ours))
    total = int(ours.size)
    return equal, total, equal / total if total else 0.0, equal == total


def compare_candidate(
    reference_name: str,
    reference_type: str,
    parameters: str,
    reference_matrix: np.ndarray,
    ours_matrix: np.ndarray,
    notes: str = "",
) -> list[ComparisonRow]:
    """Compare a reference matrix against ours under common conventions."""
    reference_matrix = _as_gf2_matrix(reference_matrix)
    ours_matrix = _as_gf2_matrix(ours_matrix)
    rows: list[ComparisonRow] = []

    for row_variant_name, row_variant in _candidate_row_variants(reference_matrix):
        for transform_name, transform_fn in _transform_functions():
            transformed = transform_fn(row_variant)
            equal, total, rate, exact = _compare_arrays(transformed, ours_matrix)
            candidate_transform = transform_name
            if row_variant_name != "all_rows":
                candidate_transform = f"{row_variant_name}+{transform_name}"
            rows.append(
                ComparisonRow(
                    reference_name=reference_name,
                    reference_available=True,
                    reference_type=reference_type,
                    parameters=parameters,
                    candidate_transform=candidate_transform,
                    shape=f"{tuple(transformed.shape)} vs {tuple(ours_matrix.shape)}",
                    num_equal_entries=equal,
                    num_total_entries=total,
                    match_rate=rate,
                    exact_match=exact,
                    notes=notes,
                )
            )
    return rows


def generate_unavailable_rows(
    enabled_references: Iterable[str],
    reason_by_reference: dict[str, str] | None = None,
) -> list[ComparisonRow]:
    reason_by_reference = reason_by_reference or {}
    rows = []
    for reference_name in enabled_references:
        rows.append(
            ComparisonRow(
                reference_name=reference_name,
                reference_available=False,
                reference_type="unavailable",
                parameters=f"n={N_BCH},k={K_BCH},r={R_BCH}",
                candidate_transform="not_run",
                shape="",
                num_equal_entries=0,
                num_total_entries=0,
                match_rate=0.0,
                exact_match=False,
                notes=reason_by_reference.get(reference_name, "reference not available"),
            )
        )
    return rows


def _metadata_note(package_name: str) -> str:
    try:
        version = importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return "version=unknown, license=unknown, commit=not applicable"
    try:
        metadata = importlib.metadata.metadata(package_name)
        license_text = metadata.get("License", "unknown")
    except importlib.metadata.PackageNotFoundError:
        license_text = "unknown"
    return f"version={version}, license={license_text}, commit=not applicable"


def _matrix_from_encoding_parity(parity_matrix: np.ndarray) -> np.ndarray:
    parity_matrix = _as_gf2_matrix(parity_matrix)
    if parity_matrix.shape != (K_BCH, R_BCH):
        raise ValueError(
            f"expected encoding parity matrix shape {(K_BCH, R_BCH)}, got {parity_matrix.shape}"
        )
    return np.concatenate([parity_matrix, np.eye(R_BCH, dtype=np.uint8)], axis=0)


def probe_galois_reference() -> ReferenceMatrix:
    galois = importlib.import_module("galois")
    bch = galois.BCH(N_BCH, K_BCH)
    parity_rows = []
    basis = np.zeros(K_BCH, dtype=np.int32)
    for idx in range(K_BCH):
        basis.fill(0)
        basis[idx] = 1
        codeword = np.asarray(bch.encode(basis), dtype=np.int32)
        parity_rows.append(codeword[K_BCH:].astype(np.uint8, copy=False))
    matrix = _matrix_from_encoding_parity(np.stack(parity_rows, axis=0))
    return ReferenceMatrix(
        name="galois",
        reference_type="message_one_hot_encoding",
        parameters=f"n={N_BCH},k={K_BCH},r={R_BCH}",
        matrix=matrix,
        notes=f"source=galois Python package, {_metadata_note('galois')}",
    )


def probe_ofec_reference(ofec_path: str | None) -> ReferenceMatrix:
    if not ofec_path:
        raise RuntimeError("OFEC path not configured; use --ofec-path or BCH_REF_OFEC_PATH")
    path = Path(ofec_path)
    if not path.exists():
        raise RuntimeError("configured OFEC path does not exist")
    sys.path.insert(0, str(path))
    try:
        module = importlib.import_module("ofec.codec._ebch_lut")
        tables = module.build_syndrome_lut_tables(N_BCH, K_BCH)
        matrix = _as_gf2_matrix(tables.column_syndrome_bits)
    finally:
        try:
            sys.path.remove(str(path))
        except ValueError:
            pass
    return ReferenceMatrix(
        name="ofec",
        reference_type="reference_syndrome_table",
        parameters=f"n={N_BCH},k={K_BCH},r={R_BCH}",
        matrix=matrix,
        notes="source=OFEC_CNN configured local path, commit=unknown, license=unknown",
    )


def probe_python_bchlib_reference() -> ReferenceMatrix:
    importlib.import_module("bchlib")
    raise RuntimeError(
        "python-bchlib installed, but no public-safe bit-level BCH(255,239) adapter is implemented"
    )


def _unsupported_path_reference(name: str, path_value: str | None) -> ReferenceMatrix:
    if not path_value:
        raise RuntimeError(f"{name} path not configured")
    if not Path(path_value).exists():
        raise RuntimeError(f"configured {name} path does not exist")
    raise RuntimeError(
        f"{name} path exists, but no public-safe adapter is implemented in this tool"
    )


def _enabled_references(value: str) -> tuple[str, ...]:
    parts = tuple(part.strip() for part in value.split(",") if part.strip())
    return parts or DEFAULT_REFERENCES


def _write_rows(path: Path, rows: list[ComparisonRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def run_reference_check(args: argparse.Namespace) -> list[ComparisonRow]:
    ours = make_bch255_t2_syndrome_matrix()
    enabled = _enabled_references(args.reference)
    if "none" in enabled:
        return generate_unavailable_rows(("none",), {"none": "external references disabled"})

    rows: list[ComparisonRow] = []
    for reference_name in enabled:
        try:
            if reference_name == "galois":
                reference = probe_galois_reference()
            elif reference_name == "ofec":
                reference = probe_ofec_reference(args.ofec_path)
            elif reference_name == "python-bchlib":
                reference = probe_python_bchlib_reference()
            elif reference_name == "aff3ct":
                reference = _unsupported_path_reference("aff3ct", args.aff3ct_path)
            elif reference_name == "linux-kernel":
                reference = _unsupported_path_reference(
                    "linux-kernel", args.linux_bch_path
                )
            else:
                raise RuntimeError(f"unknown reference {reference_name!r}")
        except Exception as exc:  # noqa: BLE001 - report adapter failures gracefully.
            rows.extend(
                generate_unavailable_rows(
                    (reference_name,),
                    {reference_name: str(exc)},
                )
            )
            continue

        rows.extend(
            compare_candidate(
                reference_name=reference.name,
                reference_type=reference.reference_type,
                parameters=reference.parameters,
                reference_matrix=reference.matrix,
                ours_matrix=ours,
                notes=reference.notes,
            )
        )
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the local BCH-like syndrome matrix against optional references."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--reference",
        default=",".join(DEFAULT_REFERENCES),
        help="Comma-separated references: ofec,galois,python-bchlib,aff3ct,linux-kernel,none",
    )
    parser.add_argument("--ofec-path", default=os.environ.get("BCH_REF_OFEC_PATH"))
    parser.add_argument("--aff3ct-path", default=os.environ.get("BCH_REF_AFF3CT_PATH"))
    parser.add_argument(
        "--linux-bch-path",
        default=os.environ.get("BCH_REF_LINUX_BCH_PATH"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    rows = run_reference_check(args)
    if not rows:
        rows = generate_unavailable_rows(("none",), {"none": "no references selected"})
    _write_rows(args.output, rows)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
