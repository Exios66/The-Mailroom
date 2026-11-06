# CTO — mailroom-alignment-audit

## Strategy (Phase 1, 2026-11-06)
- **Build:** yes, all milestones M0–M5. Freezing the visualizer was rejected; the generated contract is the long-term fix for drift.
- **Direction:** pipeline-owned contract (ADR-001); Langfuse for document events (ADR-002); Observatory primary with the React review desk as a tab (ADR-003); Python-generated tokens (ADR-004); Railway retired, HF Space hosted (ADR-005).
- **Versioning:** v0.6.0 after M2 (alignment); v1.0.0 after M4 (floor v2).

## Discovery notes [CONFIRMED]
- Stack: Python FastAPI; vanilla `web/` and `hosted/`; optional React `ui/`; TUI; `terminal/`; `operator_desk/`.
- Six surfaces for one feed is the main cost driver; resolved by ADR-003.
