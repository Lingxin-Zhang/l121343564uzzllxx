# Reference Inspection Notes

This public note records reference-use policy for the trace-level benchmark
work. It is code-focused and intentionally avoids local machine paths.

## This Round

- No external repository code was copied.
- No external reference repository was committed.
- No full product-code, staircase-code, Chase-Pyndiah, OFEC, BCH, or eBCH
  decoder was implemented.
- The new workload traces are clean-room synthetic component-kernel call
  patterns.

## Reference-only Observations

- Candidate testing is modeled as repeated GF(2) syndrome computation for
  candidate error masks.
- Product-like traces use row and column component-batch events.
- Staircase-like traces use sliding-window component-batch events and small
  event-update events.
- oFEC-like traces use component syndrome, candidate-test, and event-update
  events, but remain benchmark traces only.

## Copy Policy

External repositories may be inspected for parameters, naming, and call-pattern
ideas. Implementation code must not be copied into this repository. If a future
round performs deeper reference inspection, record only reference-only
observations and clean-room design implications here.
