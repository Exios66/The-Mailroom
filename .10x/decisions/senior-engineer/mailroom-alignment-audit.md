# Senior Engineer — mailroom-alignment-audit

Status: Planning complete.

- M0: F-1 adds `pytest-asyncio` to `[dev]`. A-9 updates `AuditChain.tsx` and `api/audit.ts` to read `event`/`entry_hash`/`entry_id`, keeping the legacy keys as fallbacks. H-1 removes Railway files and keeps `listen_port()`.
- Contract loader: `PipelineSchema.load()` gains a contract layer; `MAILROOM_TAXONOMY` stays as an override.
- Interpreter: `arbitrate-classification` → `Stage.CLASSIFICATION_ARBITER` in `Phase.INTAKE_SORT`.
- Floor: replace the `STATIONS` literal in `web/js/floor.js` with a layout served from `/api/meta.topology`.
- Review desk tab: iframe `/desk/` with `?embed=1` (hides desk chrome); JWT stays in same-origin storage.
- Tricky: re-run clustering combined with loop drawing; LangGraph edge introspection; canvas hit-testing after scaling.
