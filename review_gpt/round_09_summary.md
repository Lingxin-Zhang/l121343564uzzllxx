# Round 09 Summary: Remote Access Probe and Subagent Guidance

## Modified Files

- `AGENTS.md`
- `review_gpt/latest.md`
- `review_gpt/round_09_summary.md`

## Implementation

- Added project guidance for subagent collaboration.
- Added project guidance for skill usage.
- Listed good subagent use cases: independent exploration, result review,
  parallel experiments, plot/documentation review, and code review.
- Listed tasks to avoid delegating: immediate blockers, tightly coupled edits,
  credential-sensitive work, and final verification.
- Kept secret server credentials out of tracked files.
- Stopped further remote attempts after the latest user request.

## Remote Access Probe

- SSH port probing to the provided host timed out.
- A `paramiko` SSH login attempt also timed out before authentication.
- No remote benchmark was run.

## Test Result

```text
python -m pytest tests/test_correctness.py -q
160 passed
```

## Known Issues

- The remote host is not reachable from this environment at the moment.

## Next Step

Retry after confirming network/VPN access, then run a small benchmark smoke test
before moving larger experiments to the server.
