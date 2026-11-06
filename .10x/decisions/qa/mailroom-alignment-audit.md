# QA — mailroom-alignment-audit

- [DISCOVERED] Baseline 532/535 pass. Failing: async test without pytest-asyncio in `[dev]`.
- [DISCOVERED] No contract test runs the visualizer against real current pipeline trace output; drift (e.g. `arbitrate-classification`) passes the suite silently.

## Proposed plan (2026-11-06)
See spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md` and ADR-001..004 (Proposed).
