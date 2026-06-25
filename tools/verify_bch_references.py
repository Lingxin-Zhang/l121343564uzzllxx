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
DEFAULT_REGISTRY_OUTPUT = ROOT / "results" / "raw" / "reference_registry.csv"
DEFAULT_PAIRWISE_OUTPUT = ROOT / "results" / "raw" / "bch_reference_pairwise_check.csv"
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


@dataclass(frozen=True)
class ReferenceRegistryRow:
    reference_name: str
    role: str
    suggested_url_or_repo: str
    license_status: str
    adapter_status: str
    trust_level_for_bch_math: str
    trust_level_for_ofec_structure: str
    notes: str


@dataclass(frozen=True)
class PairwiseComparisonRow:
    left_reference: str
    right_reference: str
    left_type: str
    right_type: str
    candidate_transform: str
    shape: str
    num_equal_entries: int
    num_total_entries: int
    match_rate: float
    exact_match: bool
    notes: str


def reference_registry_rows() -> list[ReferenceRegistryRow]:
    """Return the lightweight reference metadata registry."""
    return [
        ReferenceRegistryRow(
            reference_name="linux-kernel-bch",
            role="mature generic binary BCH implementation",
            suggested_url_or_repo="torvalds/linux: lib/bch.c, include/linux/bch.h",
            license_status="GPL-2.0-only; do not copy code",
            adapter_status="not configured; behavior adapter not implemented",
            trust_level_for_bch_math="high as external behavior reference if invoked",
            trust_level_for_ofec_structure="none",
            notes="Useful for BCH encode/decode, syndrome, Berlekamp-Massey, and root finding behavior checks.",
        ),
        ReferenceRegistryRow(
            reference_name="python-bchlib",
            role="Python-callable BCH package",
            suggested_url_or_repo="jkent/python-bchlib",
            license_status="external package; inspect metadata when installed",
            adapter_status="API surveyed; bit-level BCH(255,239) adapter not trusted yet",
            trust_level_for_bch_math="medium after parameter and bit-order alignment",
            trust_level_for_ofec_structure="none",
            notes="Installed API supports BCH(t=2,m=8) with n=255/ecc_bits=16, but byte-level message packing needs validation.",
        ),
        ReferenceRegistryRow(
            reference_name="galois",
            role="mathematical BCH construction/reference",
            suggested_url_or_repo="mhostetter/galois Python package",
            license_status="MIT according to installed package metadata when available",
            adapter_status="implemented through message one-hot encoding",
            trust_level_for_bch_math="high for mathematical construction",
            trust_level_for_ofec_structure="low",
            notes="Systematic encoding convention and bit ordering still need explicit comparison.",
        ),
        ReferenceRegistryRow(
            reference_name="ofec-cnn-local",
            role="local user implementation and convention reference",
            suggested_url_or_repo="local path only, stored outside tracked files",
            license_status="local user code; not copied",
            adapter_status="implemented when BCH_REF_OFEC_PATH or --ofec-path is configured",
            trust_level_for_bch_math="medium; useful but not a gold standard",
            trust_level_for_ofec_structure="high for this project convention checks",
            notes="May contain bugs; use as one reference among several.",
        ),
        ReferenceRegistryRow(
            reference_name="aff3ct",
            role="communication/FEC simulation framework",
            suggested_url_or_repo="aff3ct/aff3ct",
            license_status="external C++ project; do not copy code",
            adapter_status="not configured; behavior adapter not implemented",
            trust_level_for_bch_math="medium if a compatible BCH module is invoked",
            trust_level_for_ofec_structure="medium for benchmark/FEC framework design",
            notes="Useful for architecture and benchmark style as well as optional behavior checks.",
        ),
        ReferenceRegistryRow(
            reference_name="ofec-huawei",
            role="public C++ oFEC/Huawei-style layout reference",
            suggested_url_or_repo="zsr71/oFEC-HUAWEI",
            license_status="external repository; inspect license before use",
            adapter_status="not configured; code inspection only",
            trust_level_for_bch_math="medium after local inspection",
            trust_level_for_ofec_structure="high as oFEC organization reference",
            notes="Inspect params.hpp, bch_255_239.hpp, chase256.cpp, ofec_decoder.cpp, and ofec_encoder.cpp if cloned.",
        ),
        ReferenceRegistryRow(
            reference_name="ofec-decoder-vhdl",
            role="hardware-oriented oFEC decoder reference",
            suggested_url_or_repo="YihanLiu1010/oFEC-Decoder",
            license_status="external repository; inspect license before use",
            adapter_status="not configured; hardware structure reference only",
            trust_level_for_bch_math="low for Python behavior comparison",
            trust_level_for_ofec_structure="medium for pipeline organization",
            notes="VHDL/Chase-Pyndiah oriented; not a direct Python backend reference.",
        ),
        ReferenceRegistryRow(
            reference_name="ofec-sim",
            role="auxiliary simulation-style oFEC reference",
            suggested_url_or_repo="zsr71/oFEC-SIM",
            license_status="external repository; inspect license before use",
            adapter_status="not configured",
            trust_level_for_bch_math="low until inspected",
            trust_level_for_ofec_structure="medium if useful after inspection",
            notes="Lower priority auxiliary reference.",
        ),
        ReferenceRegistryRow(
            reference_name="automa-ofec",
            role="auxiliary small oFEC reference",
            suggested_url_or_repo="vsousa46/Automa-oFEC",
            license_status="external repository; inspect license before use",
            adapter_status="not configured",
            trust_level_for_bch_math="low",
            trust_level_for_ofec_structure="low",
            notes="Low priority; do not rely on it for correctness.",
        ),
        ReferenceRegistryRow(
            reference_name="gnuradio-volk",
            role="high-throughput stream/SIMD implementation inspiration",
            suggested_url_or_repo="GNU Radio / VOLK",
            license_status="external project; do not copy code",
            adapter_status="not a BCH correctness adapter",
            trust_level_for_bch_math="none",
            trust_level_for_ofec_structure="low",
            notes="Useful for chunk processing and SIMD kernel selection ideas, not BCH correctness.",
        ),
    ]


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


def compare_reference_pair(
    left: ReferenceMatrix,
    right: ReferenceMatrix,
) -> list[PairwiseComparisonRow]:
    """Compare two available references under common convention transforms."""
    left_matrix = _as_gf2_matrix(left.matrix)
    right_matrix = _as_gf2_matrix(right.matrix)
    rows: list[PairwiseComparisonRow] = []
    for row_variant_name, row_variant in _candidate_row_variants(left_matrix):
        for transform_name, transform_fn in _transform_functions():
            transformed = transform_fn(row_variant)
            equal, total, rate, exact = _compare_arrays(transformed, right_matrix)
            candidate_transform = transform_name
            if row_variant_name != "all_rows":
                candidate_transform = f"{row_variant_name}+{transform_name}"
            rows.append(
                PairwiseComparisonRow(
                    left_reference=left.name,
                    right_reference=right.name,
                    left_type=left.reference_type,
                    right_type=right.reference_type,
                    candidate_transform=candidate_transform,
                    shape=f"{tuple(transformed.shape)} vs {tuple(right_matrix.shape)}",
                    num_equal_entries=equal,
                    num_total_entries=total,
                    match_rate=rate,
                    exact_match=exact,
                    notes=f"left_notes={left.notes}; right_notes={right.notes}",
                )
            )
    return rows


def generate_pairwise_rows(references: list[ReferenceMatrix]) -> list[PairwiseComparisonRow]:
    if len(references) < 2:
        return [
            PairwiseComparisonRow(
                left_reference="not_enough_available_references",
                right_reference="not_enough_available_references",
                left_type="unavailable",
                right_type="unavailable",
                candidate_transform="not_run",
                shape="",
                num_equal_entries=0,
                num_total_entries=0,
                match_rate=0.0,
                exact_match=False,
                notes="pairwise comparison requires at least two available references",
            )
        ]

    rows: list[PairwiseComparisonRow] = []
    for left_idx in range(len(references)):
        for right_idx in range(left_idx + 1, len(references)):
            rows.extend(compare_reference_pair(references[left_idx], references[right_idx]))
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
    bchlib = importlib.import_module("bchlib")
    api_note = "imported bchlib"
    try:
        bch = bchlib.BCH(t=2, m=8)
        api_note = (
            f"imported bchlib; BCH(t=2,m=8) reports n={bch.n}, "
            f"ecc_bits={bch.ecc_bits}, ecc_bytes={bch.ecc_bytes}, "
            f"prim_poly={bch.prim_poly}"
        )
    except Exception as exc:  # noqa: BLE001 - record API survey result.
        api_note = f"imported bchlib but BCH(t=2,m=8) construction failed: {exc}"
    raise RuntimeError(
        f"{api_note}; byte-level message packing and exact BCH(255,239) bit order are not validated, so no public-safe adapter is enabled"
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


def _write_dataclass_rows(path: Path, rows: list[object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def collect_reference_results(
    args: argparse.Namespace,
) -> tuple[list[ComparisonRow], list[ReferenceMatrix]]:
    ours = make_bch255_t2_syndrome_matrix()
    enabled = _enabled_references(args.reference)
    if "none" in enabled:
        return (
            generate_unavailable_rows(("none",), {"none": "external references disabled"}),
            [],
        )

    rows: list[ComparisonRow] = []
    available_references: list[ReferenceMatrix] = []
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

        available_references.append(reference)
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
    return rows, available_references


def run_reference_check(args: argparse.Namespace) -> list[ComparisonRow]:
    rows, _ = collect_reference_results(args)
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare the local BCH-like syndrome matrix against optional references."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry-output", type=Path, default=DEFAULT_REGISTRY_OUTPUT)
    parser.add_argument("--pairwise-output", type=Path, default=DEFAULT_PAIRWISE_OUTPUT)
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
    rows, available_references = collect_reference_results(args)
    if not rows:
        rows = generate_unavailable_rows(("none",), {"none": "no references selected"})
    registry_rows = reference_registry_rows()
    pairwise_rows = generate_pairwise_rows(available_references)
    _write_dataclass_rows(args.output, rows)
    _write_dataclass_rows(args.registry_output, registry_rows)
    _write_dataclass_rows(args.pairwise_output, pairwise_rows)
    print(f"wrote {args.output}")
    print(f"wrote {args.registry_output}")
    print(f"wrote {args.pairwise_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
