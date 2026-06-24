# GF(2) Kernel Correctness Repository

This repository contains small GF(2) linear-kernel backends and pytest-based
correctness checks. The current focus is correctness and API consistency, not
benchmark claims.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Run Tests

```bash
pytest
```

## Implemented Modules

- `NaiveGF2Kernel`
- `SparseXorKernel`
- `BlockLUTKernel`
- `EventUpdateKernel`
- `PackedBatchGF2Kernel` correctness-first `apply_many`

## Not Yet Implemented

- `HybridPlanner`
- Formal benchmark scripts/results

Do not report performance improvements unless they come from reproducible
benchmark outputs committed with the relevant code and methodology.
