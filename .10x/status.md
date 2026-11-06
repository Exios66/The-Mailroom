# Status

**Feature:** `mailroom-alignment-audit`
**Phase:** Phase 4 (implementation). M0 and M1 consumer changes are merged;
M2 catch-up is underway. T-1 travels with pipeline T-2.

## Milestones
- [x] M0 Stop the bleeding: The-Mailroom #63; llm-mailroom #166.
- [ ] M1 Contract: producer #165 and consumer #64 merged; conformance and source
  registry shipped. The owner still needs to confirm CircleCI is enabled.
- [ ] M2 Catch-up (v0.6.0): A-7 implemented on `feat/m2-adopt-merged-contract`:
  producer 0.9.1 at `65523a220954`, Dojo 0.27.2 at `1cd4aba76d82`, exact-byte
  contract provenance. Remaining: T-1/T-2/T-3 and B-* in the producer; A-4/A-5,
  A-6/A-8/A-10/A-11, T-6/F-3 and G-4 in the visualizer.
- [ ] M3 Design system.
- [ ] M4 Floor v2 + Observatory map + review desk tab (v1.0.0).
- [ ] M5 Ops panels.

## Browser audit and source policy

PR #66 addresses live outage/reconnect races, review actions and mobile layouts.
All 11 published first-round review threads were fixed and resolved after
browser verification at its follow-up commit. This PR is not merged.
Phoenix and Langfuse are primary trace adapters; any conformant configured sink
can supply the Observatory. No local simulator or canned live fallback.

## Validation

PR #66 follow-up: 576 passed, 2 skipped; optional desk type-check/build passed;
manual browser checks include Phoenix, a custom registry adapter and injected
transport races. M2 A-7: 577 passed, 2 skipped with the actual Dojo 0.27.2 engine; pin check,
source conformance and exact upstream-byte comparison passed.
