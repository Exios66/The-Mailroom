# Senior Engineer — mailroom-alignment-audit

Status: Proposed.

- Contract loader: `pipeline_schema.PipelineSchema.load()` gains a contract layer; the bundled mirror becomes generated, and `MAILROOM_TAXONOMY` stays as an override.
- Interpreter: route `arbitrate-classification` to a new `Stage.CLASSIFICATION_ARBITER` in `Phase.INTAKE_SORT`; read the gate from the event or score, with a span-output fallback.
- Floor: replace the `STATIONS` literal in `web/js/floor.js` with a layout served from `/api/meta.topology` (computed server-side in Python, so the JS only draws).
- Tricky parts: re-run clustering (`RUN_GAP_S`) combined with loop drawing; LangGraph edge introspection; canvas hit-testing after integer scaling.
