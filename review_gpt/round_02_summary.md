# Round 02 Summary: Event Update Correctness

## Modified Files

- `linear_kernel/event_update.py`
- `linear_kernel/packed_batch.py`
- `tests/test_correctness.py`
- `AGENTS.md`
- `README.md`
- `review_gpt/latest.md`
- `review_gpt/round_02_summary.md`

## Implementation

- Added `EventUpdateKernel.update`.
- Renamed the packed batch skeleton interface to `apply_many`.
- Added correctness tests for event updates and invalid inputs.

## Test Result

```text
pytest passed
```

## Known Issues

- `PackedBatchGF2Kernel` was still skeleton-only in this round.
- `HybridPlanner` was not implemented.

## Next Step

Implement correctness-first `PackedBatchGF2Kernel.apply_many`.
