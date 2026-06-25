"""Run all micro-benchmarks and generate figures."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str]) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=ROOT, check=True)


def main() -> None:
    python = sys.executable
    run([python, "-m", "benchmarks.bench_block_width"])
    run([python, "-m", "benchmarks.bench_density"])
    run([python, "-m", "benchmarks.bench_batch"])
    run([python, "-m", "benchmarks.bench_stream"])
    run([python, "-m", "benchmarks.bench_bch_syndrome"])
    run([python, "scripts/plot_results.py"])


if __name__ == "__main__":
    main()
