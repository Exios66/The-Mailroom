---
name: pipeline-schema-sync
description: Keep The-Mailroom topology mirror in sync with llm-mailroom (pipeline_schema.py, trace_interpreter.py, fake_langfuse fixtures, SPAN_STAGE_MAP, DOC_CLASSES, scores). Use when upstream graph, taxonomy, span names, observation types, or judge scores change — the #1 maintenance duty.
---

# Pipeline schema sync

**When:** `llm-mailroom` changes nodes, `taxonomy.yaml`, span names, observation
types, agent roster, doc classes, subclasses, or score names.

Pipeline facts are no longer hand-copied. The pipeline publishes a generated
display contract (`contract/mailroom-contract.json`, ADR-001) and this repo
vendors it:

```bash
python scripts/bump_producer_pin.py <40-char sha> --version <x.y.z> --checkout ../llm-mailroom
python -m pytest tests/test_contract_conformance.py tests/test_bump_producer_pin.py
```

The bump moves the pin everywhere except history, copies the contract into
`mailroom_ui/contract/`, and records provenance in `contract/source.json`.
Then fix every gap `contract_gaps()` reports (floor stage, phase, agent label,
read score) in one change: schema + interpreter + tests + CHANGELOG.

## Still local (visualizer decisions)

| File | What |
| --- | --- |
| `mailroom_ui/pipeline_schema.py` | `SPAN_STAGE_MAP`, `STAGE_PHASE`, `NODE_ORDER`, agent labels, `READ_SCORE_NAMES` |
| `mailroom_ui/trace_interpreter.py` | metadata/input/output, `type` / v4 `observationType` handling |
| `hosted/js/app.js` | `SPAN_STAGE` for live envelopes (checked by the conformance test) |
| `tests/fake_langfuse.py` | v2/v3 `make_trace` **and** v4 `make_trace_v4` |

Live override: `MAILROOM_TAXONOMY` → absolute path to the pipeline taxonomy.
Cached at process level — **restart** after edits.

## Breakage map

| Upstream change | Symptom here |
| --- | --- |
| New span / graph id | Envelope sits in `unknown` / INBOX |
| New doc class | Gray default stamp |
| Renamed judge scores | Verdict/quality vanish |
| New env/tag | Filters in `.env` miss runs |
| New observation type | Node hidden or filed as generation |

Offline evaluation uses
Dojo through optional `[eval]` (`@4740d768`, Dojo v0.24.2); do not duplicate its scoring engine
or make the live display path import it.

Producer **code** pin (separate from the topology mirror): extra `[pipeline]`
installs dist `mailroom` `@65523a220954d05bdf9b3d6604eb2fe128342f58` (0.9.1, reviewed source adoption). Import only through
`mailroom_ui/producer.py` (`pipeline.review_resolve`, `schemas.manifest`).
Never import `api.main`. Move the pin only with `scripts/bump_producer_pin.py`.

## Related

- Router: [mailroom-tool-router](../mailroom-tool-router/SKILL.md)
- Process: `AGENTS.md` (“Sister repo” + “What we mirror”)
- HF catalogs: [huggingface](../huggingface/SKILL.md)
