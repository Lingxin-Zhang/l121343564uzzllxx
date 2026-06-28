"""Round32 multi-round Fig3 fixed-map throughput benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from benchmarks._common import RAW_DIR, ensure_result_dirs
from benchmarks.bench_fixed_map_three_backend import (
    _parse_int_list,
    default_matrix_specs,
    run_three_backend_rows,
)
from benchmarks.bench_round31_cache_width import _try_set_affinity
from benchmarks.round32_common import annotate_probe_fields, normalize_rows_by_probe, write_dynamic_csv

DEFAULT_OUTPUT = RAW_DIR / "round32_fig3_throughput_rounds.csv"


def run_round32_fixed_map_rounds(
    *,
    batch_sizes: tuple[int, ...],
    long_batch_sizes: tuple[int, ...],
    rounds: int,
    repeats: int,
    warmups: int,
    block_width: int,
    max_in_memory_rows: int,
    max_timed_batch_size: int,
    max_galois_batch_size: int,
    seed: int,
    cpu_core: int | None,
    probe_iterations: int,
) -> list[dict]:
    spec = default_matrix_specs()[0]
    affinity_status = _try_set_affinity(cpu_core)
    all_rows: list[dict] = []
    widths = {
        (spec.profile, "syndrome"): int(block_width),
        (spec.profile, "parity"): int(block_width),
    }
    for round_index in range(int(rounds)):
        rows = run_three_backend_rows(
            matrix_specs=(spec,),
            batch_sizes=batch_sizes,
            long_batch_sizes=long_batch_sizes,
            repeats=repeats,
            warmups=warmups,
            block_widths_by_task=widths,
            default_block_width=block_width,
            include_galois=True,
            max_in_memory_rows=max_in_memory_rows,
            max_timed_batch_size=max_timed_batch_size,
            max_galois_batch_size=max_galois_batch_size,
            seed=seed,
        )
        annotated = annotate_probe_fields(rows, round_index=round_index, probe_iterations=probe_iterations)
        for row in annotated:
            row["affinity_status"] = affinity_status
        all_rows.extend(annotated)
    return normalize_rows_by_probe(all_rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Round32 multi-round fixed-map throughput benchmark.")
    parser.add_argument("--batch-sizes", default="1,10,100,1000,10000,100000")
    parser.add_argument("--long-batch-sizes", default="")
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=30)
    parser.add_argument("--block-width", type=int, default=14)
    parser.add_argument("--max-in-memory-rows", type=int, default=100_000)
    parser.add_argument("--max-timed-batch-size", type=int, default=100_000)
    parser.add_argument("--max-galois-batch-size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--cpu-core", type=int, default=None)
    parser.add_argument("--probe-iterations", type=int, default=200_000)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    ensure_result_dirs()
    rows = run_round32_fixed_map_rounds(
        batch_sizes=_parse_int_list(args.batch_sizes),
        long_batch_sizes=_parse_int_list(args.long_batch_sizes),
        rounds=args.rounds,
        repeats=args.repeats,
        warmups=args.warmups,
        block_width=args.block_width,
        max_in_memory_rows=args.max_in_memory_rows,
        max_timed_batch_size=args.max_timed_batch_size,
        max_galois_batch_size=args.max_galois_batch_size,
        seed=args.seed,
        cpu_core=args.cpu_core,
        probe_iterations=args.probe_iterations,
    )
    write_dynamic_csv(args.output, rows)
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
