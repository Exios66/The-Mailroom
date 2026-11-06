# Staff Engineer — mailroom-alignment-audit

- [DISCOVERED] Conventions: DMR-NNN ticket prefixes, Keep-a-Changelog, semver via `scripts/release.py`, skills under `.cursor/skills/` (`pipeline-schema-sync` is the sync playbook).
- [DISCOVERED] Pin SHA duplicated across producer.py, pyproject.toml, README, wiki, 3 skills, AGENTS.md. CHANGELOG claims pin `4c274a4` while code says `1a1ec3d` — docs/code disagree.
- [DISCOVERED] UI logic duplicated across web/js, hosted/js, ui/src, tui — each re-implements stage colors, doc-class stamps, labels.
- [DISCOVERED] Test fixtures (`tests/fake_langfuse.py`) mirror the trace contract by hand; no fixture is generated from real pipeline output.

## Proposed plan (2026-11-06)
See spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md` and ADR-001..004 (Proposed).

## Standards for this feature
- One pin-bump command (`scripts/bump_producer_pin.py`) moves the SHA everywhere; tests assert that every location agrees.
- Generated files (contract, tokens) are committed and checked for freshness in tests.
- The AGENTS.md "verify manually" frontend rule is replaced by Python Playwright smoke tests (F-4); still no JS test harness.
