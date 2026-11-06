# SDE — mailroom-alignment-audit

## M0 (built 2026-11-06)
- **A-9:** `ui/src/components/AuditChain.tsx` reads producer `entry_id`/`event`/`entry_hash` (legacy `id`/`action`/`hash` fallbacks), shows `actor`/`detail`, and nests sub-rows by `parent_id`. `AuditEntry` type widened. Test: `test_audit_chain_reads_producer_field_names`.
- **F-1:** `pytest-asyncio>=0.23` in `[dev]`.
- **H-1 (visualizer):** deleted `.railway/` and `nixpacks.toml`; `_platform()` no longer reports `railway`; Dockerfile `ARG MAILROOM_BUILD_SHA`; docs, wiki, README, AGENTS and `.env.example` point at the HF Space. `tests/test_railway_deploy.py` → `tests/test_platform_deploy.py` (+ `test_railway_is_retired`).
- **H-1 (pipeline, separate PR):** `railway.json` and `nixpacks.toml` deleted. The Phoenix auto-skip guard and the bind-error hint now key on `SPACE_ID`/`HF_SPACE_ID` instead of `RAILWAY_*`. `test_railway_listen.py` → `test_listen_guards.py`. Deployment docs rewritten. Historical CHANGELOG and spec entries left as written; the generated `tree.html` is untouched.

## M1 started
- **A-1 (pipeline PR llm-mailroom#165):** `src/scripts/export_contract.py` → `contract/mailroom-contract.json` (contract 1.0.0; 14 nodes, 46 edges, 18 spans, 16 agents, 5 classes, 59 scores). `traced_node` sets `mailroom_span_name`; `intake-ml-triage` added to `NODE_OBSERVATION_TYPES`.

## M1 consumer (built 2026-11-06)
- **A-2:** `scripts/bump_producer_pin.py` moves the full and short pin in every non-history file, moves the package version only on lines that carry the SHA, vendors the contract and writes `contract/source.json` (commit, versions, sha256, origin, `matches_pin`, note). `--check` fails on stale pin references and on a hand-edited or unexplained provisional contract. A5 fixed: `959bb0b` / `3cf9fb9` references removed.
- **A-3:** `pipeline_schema.py` derives classes, labels, specialists, fields, subclasses, agents, observation types, failure classes, score aliases/configs and thresholds from the contract. Local: `SPAN_STAGE_MAP`, `STAGE_PHASE`, `NODE_ORDER`, agent display, failure labels, `READ_SCORE_NAMES`. Contract major version is checked at import.
- **F-2:** `contract_gaps()` checks both directions (contract → floor and floor → contract); tests cover the vendored contract, a renamed span, a new node/agent/failure class, a removed read score, and the Observatory `SPAN_STAGE` table.
- **T-4:** `mailroom_ui/source_registry.py`; `MAILROOM_SOURCE` is a comma list (`both` alias kept); entry-point group `mailroom.sources`.
- **T-5:** `tests/source_conformance.py`, with 3 golden traces (archived, review with re-classify + classification arbiter, aborted) rendered for Langfuse and Phoenix; fingerprints match.
- **H-2:** `.circleci/config.yml` (`python`, `desk`). Token and Playwright steps are added in M3 and M4.

## Deviations
- ADR-005 replaced the planned IaC migration with removal.
- The Phoenix guard was generalised to HF Spaces, which keeps its intent: hosted containers have no local collector.

- A-4 interim: `classification_arbiter` / `arbitrate-classification` land on the re-classify station; a dedicated stage is still planned in M2 (A-4).
- T-1 (`trace_schema` in the contract) ships with T-2 in M2, so the contract never lists attributes the pipeline does not emit yet.
- The kit found one backend difference: Langfuse lists the root chain as an observation and Phoenix does not. The fingerprint excludes the root (it is the run, not a station).
- The vendored contract is from #165's head (`cc28cd4`), not the pin, and says so in `source.json`.

## Tech debt
- `tree.html` in llm-mailroom still lists `railway.json` (a generated artifact).
