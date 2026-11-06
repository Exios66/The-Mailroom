# Engineering Manager — mailroom-alignment-audit

Status: **Planning complete** 2026-11-06.

| Milestone | Tasks | Est. | Repo(s) |
|---|---|---|---|
| M0 Stop the bleeding | F-1, A-9, H-1 | 2 d | both |
| M1 Contract | A-1, A-2, A-3, F-2, H-2, T-1, T-4, T-5 | 7.5 d | both |
| M2 Catch-up → v0.6.0 | A-4..A-8, A-10, A-11, T-2, T-3, T-6, B-1..B-4, F-3, G-4 | 11 d | both |
| M3 Design system | D-1, D-2, G-2 | 3 d | visualizer |
| M4 Floor v2 + map + review desk → v1.0.0 | D-3..D-8, C-1..C-4, F-4, I-1, I-2 | 14–16 d | visualizer |
| M5 Ops panels | E-1, E-2, G-1, G-3 | 3 d | visualizer |

Each milestone ships as its own PR per repo, stacked on the plan branch.
CI note (H-2): GitHub Actions is unavailable on this account. CircleCI is the target, and needs the owner to enable the project in CircleCI.

## Re-plan (ADR-006)
New workstream T (T-1..T-6, about 7 d). M1 rises to 7.5 d and M2 to 9.5 d. B tasks now emit through the T-2 layer.
