# ADR-003: Surface roles and React desk maintenance mode

**Status:** Proposed (owner decision 3)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit

## Context
Six surfaces render one feed; each re-implements labels and colours.

## Decision
The Observatory (`hosted/`) is the primary desk. The pixel console (`web/`) is the signature floor. The TUI keeps label and stage parity only. `terminal/` is a static showcase. The React desk (`ui/`) goes into maintenance mode: bug fixes only, no new features.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Keep all six at full parity | No loss | 4–6× effort per change | Unsustainable |
| Retire `ui/` now | Less code | Breaks hub consumers that mount `/desk` | Freeze first, retire later |

## Consequences
- Parity work concentrates on two surfaces; `ui/` may lag behind by design.
