"""Round32 multi-round block-width throughput benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks._common import RAW_DIR, ensure_result_dirs
from benchmarks.bench_fixed_map_three_backend import _parse_int_list
from benchmarks.bench_round31_cache_width import (
    DEFAULT_MAX_IN_MEMORY_ROWS,
    DEFAULT_MAX_LUT_TABLE_BYTES,
    _parse_profile_keys,
    run_round31_cache_width_rows,
)
from benchmarks.round32_common import annotate_probe_fields, normalize_rows_by_probe, write_dynamic_csv

DEFAULT_OUTPUT = RAW_DIR / "round32_width_throughput_rounds.csv"


def run_round32_width_rounds(
    *,
    profiles: tuple[str, ...],
    task: str,
    batch_sizes: tuple[int, ...],
    block_widths: tuple[int, ...],
    rounds: int,
    repeats: int,
    warmups: int,
    max_in_memory_rows: int,
    max_lut_table_bytes: int,
    seed: int,
    cpu_core: int | None,
    probe_iterations: int,
) -> list[dict]:
    all_rows: list[dict] = []
    for round_index in range(int(rounds)):
        rows = run_round31_cache_width_rows(
            profile_keys=profiles,
            task=task,
            batch_sizes=batch_sizes,
            block_widths=block_widths,
            repeats=repeats,
            warmups=warmups,
            max_in_memory_rows=max_in_memory_rows,
            max_lut_table_bytes=max_lut_table_bytes,
            seed=seed,
            cpu_core=cpu_core,
            measurement_modes=("natural",),
        )
        all_rows.extend(annotate_probe_fields(rows, round_index=round_index, probe_iterations=probe_iterations))
    return normalize_rows_by_probe(all_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Round32 multi-round width sweep.")
    parser.add_argument("--profiles", default="255_239,255_231")
    parser.add_argument("--task", choices=("syndrome", "parity"), default="syndrome")
    parser.add_argument("--batch-sizes", default="1000")
    parser.add_argument("--block-widths", default=",".join(str(v) for v in range(4, 25)))
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=30)
    parser.add_argument("--max-in-memory-rows", type=int, default=DEFAULT_MAX_IN_MEMORY_ROWS)
    parser.add_argument("--max-lut-table-bytes", type=int, default=DEFAULT_MAX_LUT_TABLE_BYTES)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu-core", type=int, default=None)
    parser.add_argument("--probe-iterations", type=int, default=200_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_round32_width_rounds(
        profiles=_parse_profile_keys(args.profiles),
        task=args.task,
        batch_sizes=_parse_int_list(args.batch_sizes),
        block_widths=_parse_int_list(args.block_widths),
        rounds=args.rounds,
        repeats=args.repeats,
        warmups=args.warmups,
        max_in_memory_rows=args.max_in_memory_rows,
        max_lut_table_bytes=args.max_lut_table_bytes,
        seed=args.seed,
        cpu_core=args.cpu_core,
        probe_iterations=args.probe_iterations,
    )
    write_dynamic_csv(args.output, rows)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
