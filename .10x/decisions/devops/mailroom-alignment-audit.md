# DevOps — mailroom-alignment-audit

- [DISCOVERED] Visualizer deploys: Railway IaC (`.railway/railway.py`, declares both services), HF Docker Space (`scripts/publish_space.py`), GitHub Pages from gh-pages branch (no Actions), Dockerfile + nixpacks.
- [DISCOVERED] **Risk:** pipeline still ships `railway.json` (Config as Code), which Railway stops honoring **2026-12-01** (25 days). Visualizer IaC `preserve()`s the producer service but the producer's own config migration is not done.
- [DISCOVERED] No CI in the visualizer repo (no `.github/workflows`); pipeline uses CircleCI.

## Proposed plan (2026-11-06)
See spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md` and ADR-001..004 (Proposed).
