# ADR-003: Surface roles; the React desk becomes the Observatory review desk tab

**Status:** Accepted (2026-11-06)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit

## Context
Six surfaces render one feed, and each re-implements labels and colours. The owner wants the Observatory as the primary desk, with the React desk folded in as a tab and focused on the human review tray.

## Decision
- The Observatory (`hosted/`) is the primary desk.
- The React desk (`ui/`) is the **Review desk** tab inside the Observatory. It is mounted same-origin from `ui/dist` (`/desk`), shares the operator JWT, and is scoped to the human review tray: queue, source preview, extraction editor, dispositions, audit chain.
- When `ui/dist` is not built, the tab falls back to the Observatory's vanilla review queue. The Observatory itself stays vanilla with no Node toolchain.
- The pixel console (`web/`) is the signature floor. The TUI keeps label and stage parity. `terminal/` is a static showcase.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Freeze the React desk | Less work | The best review UX goes unused | Owner chose to repurpose it |
| Rebuild the review tray in vanilla JS | No Node at all | Duplicates working React components | More code for the same result |
| Make the Observatory React | One stack | Breaks the vanilla-hosted rule; large rewrite | Out of scope |

## Consequences
- The review desk needs Node only at build time; the Observatory works without it.
- Review-tray features land in React first; the vanilla fallback stays at its current scope.
