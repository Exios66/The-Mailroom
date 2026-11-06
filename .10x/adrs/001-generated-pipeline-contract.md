# ADR-001: Generated pipeline contract as the alignment mechanism

**Status:** Accepted (2026-11-06)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit
**Author:** 10x-Team (Architect + Staff Engineer)

## Context
The visualizer mirrors pipeline topology by hand (`pipeline_schema.py`, `trace_interpreter.py`, fixtures). The mirror is 80 commits behind and misses `classification_arbiter`, the extraction gate and two agents. The pipeline roadmap adds a scoring node family and `audit_failed` next. Nothing detects drift.

## Decision
llm-mailroom exports `contract/mailroom-contract.json` (nodes, edges, span→observation type, agents, classes, subclasses, failure classes, score names, thresholds, `contract_version`, `pipeline_sha`) from its own constants, with a CircleCI staleness check. The-Mailroom vendors the file at the pinned SHA through `scripts/bump_producer_pin.py`, derives topology from it, and keeps only display metadata locally. Unknown spans render as a visible UNMAPPED chip and are counted on `/api/health`.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Hand resync plus drift test importing the pipeline | Small | Heavy deps in CI; still a hand copy | Breaks again at pipeline stage 2 |
| Runtime import of pipeline modules | No copy | Violates the import-isolation rule; heavy image | Rejected by AGENTS.md policy |
| Freeze the visualizer | Zero cost | Loses review resolve and the floor | Not acceptable |

## Consequences
### Positive
- Drift fails CI; new nodes appear without visualizer code.
### Negative
- A small pipeline PR plus a contract semver to maintain.
### Risks
- LangGraph introspection instability: fall back to an explicit node and edge list tested against `build_graph`.

## Dependencies
- Pipeline PR A-1. Constrains ADR-004 (colours keyed by contract IDs).
