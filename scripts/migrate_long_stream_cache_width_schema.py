"""Migrate long-stream cache-width CSVs to explicit bits/bytes fields."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATHS = (
    ROOT / "results" / "raw" / "long_stream_cache_width.csv",
    ROOT / "results" / "raw" / "long_stream_cache_width_replication.csv",
)


def _parse_int(value: str) -> int:
    return int(float(str(value).strip()))


def _stream_input_bits(row: dict[str, str]) -> int:
    if str(row.get("stream_input_bits", "")).strip():
        return _parse_int(row["stream_input_bits"])
    if str(row.get("stream_input_bytes", "")).strip():
        return _parse_int(row["stream_input_bytes"])
    return _parse_int(row["num_words"]) * _parse_int(row["component_n"])


def _fieldnames(existing: list[str]) -> list[str]:
    names = [name for name in existing if name != "stream_input_bits"]
    if "stream_input_bytes" not in names:
        raise ValueError("CSV is missing stream_input_bytes")
    insert_at = names.index("stream_input_bytes")
    return names[:insert_at] + ["stream_input_bits"] + names[insert_at:]


def migrate_csv(path: Path) -> bool:
    if not path.exists():
        return False

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        fieldnames = _fieldnames(list(reader.fieldnames))
        rows = list(reader)

    migrated = []
    for row in rows:
        stream_input_bits = _stream_input_bits(row)
        migrated.append(
            {
                **row,
                "stream_input_bits": str(stream_input_bits),
                "stream_input_bytes": str((stream_input_bits + 7) // 8),
            }
        )

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in migrated)
    return True


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Migrate long-stream cache-width raw CSVs to explicit bits/bytes schema."
    )
    parser.add_argument("paths", nargs="*", type=Path, default=list(DEFAULT_PATHS))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    for path in args.paths:
        if migrate_csv(path):
            print(f"migrated {path}")
        else:
            print(f"skipped missing {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
