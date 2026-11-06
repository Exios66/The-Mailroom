# ADR-004: Shared design tokens generated in Python

**Status:** Proposed
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit

## Context
89 hex literals across surfaces; three unrelated sets of CSS custom properties; no Node allowed in `web/` and `hosted/`.

## Decision
`design/tokens.json` is the single source. `scripts/build_tokens.py` (stdlib) generates CSS custom properties for web, hosted and ui, plus Rich styles for the TUI. Palettes are keyed by contract IDs (stage, class, verdict, failure). A pytest validator checks contrast and colour-vision distinguishability.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Style Dictionary (npm) | Mature | Adds Node to the toolchain | Violates the no-Node rule |
| Hand-synced CSS files | No tooling | The status quo that caused the drift | — |

## Consequences
- Generated files are committed; CI checks that they are fresh.
