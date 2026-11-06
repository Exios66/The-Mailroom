# Security — mailroom-alignment-audit

- [DISCOVERED] Operator JWT auth hardened across DMR-111/113 (no default admin seeding on public, HMAC key preserved). Test env emits InsecureKeyLengthWarning (20-byte test key) — test-only.
- [DISCOVERED] Producer import pinned by immutable SHA; display path never imports `api.main` or `llm_dojo_scoring`.
- Audit scope to add: WS origin checks, public `/live` data exposure (PII masking relies on pipeline curation), dependency audit for ui/ npm tree.

## Proposed plan (2026-11-06)
See spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md` and ADR-001..004 (Proposed).
