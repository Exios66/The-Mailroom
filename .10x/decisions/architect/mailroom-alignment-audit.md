# Architect — mailroom-alignment-audit

## Data flow [DISCOVERED]
llm-mailroom LangGraph → traced_node spans → Langfuse (US, project `llm-mailroom`) → `langfuse_source.py` → `trace_interpreter.py` (+ `pipeline_schema.py`) → `PipelineRun` → `server/poller.py` → WS/REST → web / hosted / ui / tui.
Producer import seam: `mailroom_ui/producer.py` only (`pipeline.review_resolve`, `schemas.manifest`) pinned by SHA.

## Topology drift vs pipeline @ da07cc2 [DISCOVERED]
| Upstream (pipeline) | Visualizer | Effect |
|---|---|---|
| Graph node `classification_arbiter` / span `arbitrate-classification` (agent) | Missing from `SPAN_STAGE_MAP`, `NODE_OBSERVATION_TYPES`, `Stage`, `NODE_ORDER` | Parked classifications render as `unknown` stage |
| Extraction gate (`agents.extraction_gate`, state `extraction_gate`, audit entry) | Not modeled | Gate verdicts invisible |
| Agents `gmail_triage`, `relations` in taxonomy | Missing from `AGENTS` roster | Not displayed |
| Relations clerk / relations graphs, pager, ops_monitor, watchdog, LiteLLM gateway tiers → Modal GPU, free-model swarm, decision reviewer | No visualization | Major pipeline capabilities absent from the console |
| Sorter `sorter_v15` + Dojo sorter-guide subclass catalog | Catalogs cite Dojo v0.16.0 | Subclass labels may be stale |
| Dojo v0.27.2 (pipeline) | Eval pin interim post-0.24.2 `718e326` | Offline eval scores diverge from pipeline scoring |
| Schema provenance comments cite `@959bb0b` | Pin is `1a1ec3d`, main is `da07cc2` | Provenance unreliable |
`intake-ml-triage` is in the visualizer but not in upstream `NODE_OBSERVATION_TYPES` (still emitted from build_graph.py:608) — fine, keep.

## Structural issue
No machine-checked contract between repos. Every pipeline change requires a manual mirror PR.

## Proposed plan (2026-11-06)
See spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md` and ADR-001..004 (Proposed).

## Phase 2 design (accepted 2026-11-06)
- ADR-001 contract: llm-mailroom `src/scripts/export_contract.py` → `contract/mailroom-contract.json`; vendored at `mailroom_ui/contract/`.
- ADR-002: gate, triage and decision-review telemetry added in the pipeline; process status read from producer HTTP.
- ADR-003: React desk at `/desk`, embedded as an Observatory tab; vanilla fallback.
- ADR-005: Railway removed; HF Space pair.
- Failure modes: contract missing or invalid → fall back to the bundled mirror and report it on `/api/health`; unknown span → UNMAPPED chip; producer down → review desk read-only, with a banner.

## ADR-006 (2026-11-06)
Document traces are the displayed events on any backend. The contract gains `trace_schema`; the pipeline emits to every configured sink through an OTel-based layer; the visualizer has a source registry and a conformance kit. Finding: with the Phoenix provider, today's pipeline emits no root or node spans, so a Phoenix-only setup cannot drive the floor.
