# Engineering Manager — mailroom-alignment-audit

Status: Proposed. See spec §6–§7.

| Milestone | Est. | Gate |
|---|---|---|
| M0 Stop the bleeding (F-1, A-9, H-1) | 1.5 d | Suite green; pipeline on IaC |
| M1 Contract (A-1..A-3, F-2, H-2) | 5 d | CI fails on a renamed span |
| M2 Catch-up (A-4..A-8, B-*, F-3) | 5 d | v0.6.0 |
| M3 Design system (D-1, D-2, G-2) | 3 d | Validator green |
| M4 Floor v2 + map (D-3..D-8, C-*, F-4, I-*) | 10–12 d | v1.0.0 |
| M5 Ops panels (E-*, G-1, G-3), optional | 3 d | No operator fields public |

Critical path: H-1 (2026-12-01 deadline), then the A-1 pipeline PR, then everything else.
Cross-repo: A-1, B-1..B-4 and H-1 are llm-mailroom PRs.
