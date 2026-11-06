# SDE — mailroom-alignment-audit

## M0 (built 2026-11-06)
- **A-9:** `ui/src/components/AuditChain.tsx` reads producer `entry_id`/`event`/`entry_hash` (legacy `id`/`action`/`hash` fallbacks), shows `actor`/`detail`, and nests sub-rows by `parent_id`. `AuditEntry` type widened. Test: `test_audit_chain_reads_producer_field_names`.
- **F-1:** `pytest-asyncio>=0.23` in `[dev]`.
- **H-1 (visualizer):** deleted `.railway/` and `nixpacks.toml`; `_platform()` no longer reports `railway`; Dockerfile `ARG MAILROOM_BUILD_SHA`; docs, wiki, README, AGENTS and `.env.example` point at the HF Space. `tests/test_railway_deploy.py` → `tests/test_platform_deploy.py` (+ `test_railway_is_retired`).
- **H-1 (pipeline, separate PR):** `railway.json` and `nixpacks.toml` deleted. The Phoenix auto-skip guard and the bind-error hint now key on `SPACE_ID`/`HF_SPACE_ID` instead of `RAILWAY_*`. `test_railway_listen.py` → `test_listen_guards.py`. Deployment docs rewritten. Historical CHANGELOG and spec entries left as written; the generated `tree.html` is untouched.

## M1 started
- **A-1 (pipeline PR llm-mailroom#165):** `src/scripts/export_contract.py` → `contract/mailroom-contract.json` (contract 1.0.0; 14 nodes, 46 edges, 18 spans, 16 agents, 5 classes, 59 scores). `traced_node` sets `mailroom_span_name`; `intake-ml-triage` added to `NODE_OBSERVATION_TYPES`.

## Deviations
- ADR-005 replaced the planned IaC migration with removal.
- The Phoenix guard was generalised to HF Spaces, which keeps its intent: hosted containers have no local collector.

## Tech debt
- `tree.html` in llm-mailroom still lists `railway.json` (a generated artifact).
