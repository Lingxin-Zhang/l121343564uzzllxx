# Archived Review Note: Correctness Backends

## Code Changes

- Implemented correctness-first GF(2) backends:
  - `NaiveGF2Kernel`
  - `SparseXorKernel`
  - `BlockLUTKernel`
- Added GF(2) input validation helpers.
- Added pytest coverage for single-input and batch correctness.

## Test Result

Tests passed for the implemented correctness checks at the time of this note.

## Known Issues

- Packed batch execution was not implemented in this archived round.
- Planner and formal benchmark workflows were not implemented.

## Next Step

Continue with correctness-first batch backend coverage before adding benchmark
logic.
