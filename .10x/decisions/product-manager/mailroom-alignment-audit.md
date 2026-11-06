# Product Manager — mailroom-alignment-audit

Status: Proposed (spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md`)

## Users
- Operators resolving REVIEW items (Observatory, TUI).
- Public and stakeholder viewers of the live floor (`/live`, pixel console, gh-pages).
- Maintainers syncing with the pipeline.

## Success criteria
1. Zero unmapped spans on golden traces for every route at the pinned SHA.
2. A renamed pipeline span fails visualizer CI.
3. The floor shows retries, both arbiters, the judge loop and the gate for every run.
4. One token source; every categorical colour ≥ 3:1 contrast.
5. The pipeline deploys under Railway IaC before 2026-12-01.

## Scope options
M0–M4 core; M5 (ops and relations panels) optional. Owner decisions are listed in spec §9.
