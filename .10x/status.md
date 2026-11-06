# Status

**Feature:** `mailroom-alignment-audit`
**Phase:** Phase 0: full plan proposed. Waiting on owner decisions (spec §9).
**Date:** 2026-11-06

## Artifacts
- Spec: `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md`
- ADRs (Proposed): 001 contract, 002 operational state, 003 surface roles, 004 design tokens

## Baseline
- Visualizer v0.5.1 @ cab7a41; pipeline v0.9.1+ @ da07cc2; producer pin 1a1ec3d (80 commits behind).
- Tests: 532 passed, 2 skipped, 1 failed (pytest-asyncio missing from `[dev]`).

## Milestones (not started)
- [ ] M0 Stop the bleeding
- [ ] M1 Contract
- [ ] M2 Catch-up (v0.6.0)
- [ ] M3 Design system
- [ ] M4 Floor v2 + Observatory map (v1.0.0)
- [ ] M5 Ops panels (optional)

## Deadline
- Railway Config as Code ends 2026-12-01: the pipeline's `railway.json` must be migrated (H-1).
