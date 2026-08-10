# Architecture

> This file is mirrored at `wiki/Architecture.md` — edit both together (see
> `wiki/sync-wiki.sh`). This page describes the architecture of The-Mailroom,
> the visual engine for the `llm-mailroom` pipeline. For the pipeline's own
> architecture see the sister repo's docs (`../llm-mailroom`).

## Overview

The-Mailroom is a pixel-art console that renders every run of the
`llm-mailroom` multi-agent legal-document pipeline from its Langfuse traces.
**Langfuse is the sole source of truth**: no display value is ever fabricated
or served from local canned data. The repo is read-only against Langfuse
(project-scoped API keys, backend proxies everything — the browser never holds
keys).

```
┌────────────────────────── Langfuse (US cloud, project llm-mailroom) ──────┐
│  traces · observations (spans/generations) · scores · sessions            │
└────────────▲──────────────────────────────────────────────▲────────────────┘
             │ project-scoped API keys (read-only)          │
┌────────────┴──────────────── The-Mailroom ────────────────┴────────────────┐
│ mailroom_ui/  langfuse_source.py ← adapter (trace/observations/scores/     │
│               trace_interpreter.py ← sessions via SDK)                    │
│               pipeline_schema.py ← topology mirror (taxonomy.yaml)        │
│               metrics.py · models.py                                       │
│ server/  FastAPI :8001 → /api/* + /ws → serves web/                        │
│ web/     pixel-art SPA: Floor (conveyor) · Inspector · Sessions ·          │
│          Metrics · Console                                                 │
│ tui/     rich-based console (planned)                                      │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data flow

1. `server/poller.py` `PollHub` polls `list_recent_runs()` every
   `MAILROOM_POLL_INTERVAL` seconds. `list_recent_runs` uses **trace-list
   responses only** ("light" runs) — cheap enough to poll continuously.
2. Each light run is interpreted by `trace_interpreter.interpret_trace` and
   compacted by `poller.floor_payload` (stage, doc type, confidences, verdict,
   cost, …).
3. Full drill-down (`/api/traces/{id}`) fetches observations + scores on
   demand via `LangfuseSource.get_run()`; `PollHub` keeps a small per-trace
   detail cache.
4. Snapshots are broadcast over WebSocket `/ws`; the SPA renders the floor,
   sessions, metrics, and console from the same payloads.

## Interpreting traces

A `document-pipeline` trace carries:

- **Trace fields**: `id` (deterministic, seeded from filename), `name`,
  `timestamp`, `latency`, `session_id` (= matter_id, or a run-scoped session
  for pilots), `environment`, `tags` (`[mailroom, <env>, run-<n>, ...]`),
  `metadata` (`{attempt, run_id, run_deadline}`), curated `input`/`output`.
- **Node spans**: verb-first names mapped to stages by
  `pipeline_schema.SPAN_STAGE_MAP` (`ingest-document`, `classify-document`,
  `extract-fields`, `route-for-review`, `adjudicate-conflict`,
  `compile-report`, `write-catalog`, `archive-document`, …).
- **Generations**: auto-traced LLM calls (model, usage, latency,
  `cost_details`).
- **Scores**: confidences, run metrics, judge verdict
  (`mailroom-pipeline-judge` CORRECT/PARTIAL/MISS) and quality
  (`mailroom-pipeline-quality` 0–1).

Because pilot/attempt re-runs reuse the deterministic trace id, a single
trace can carry several full runs. The interpreter clusters observations by
time gap (`RUN_GAP_S`) and keeps only the latest cluster — one envelope per
trace, showing the latest run.

## Pipeline topology mirror

`pipeline_schema.py` bundles a mirror of the pipeline's graph
(`graph/routing.py` + `config/taxonomy.yaml`): node/span names, stage→phase
mapping, agent roster, doc classes, specialist dispatch, and confidence
thresholds. The `MAILROOM_TAXONOMY` env var can point at the live
`taxonomy.yaml` so thresholds/doc classes come straight from the pipeline
config instead of the mirror (cached at process level — restart to reload).

When the pipeline changes (new span, doc class, score, tag, env), the mirror
must be updated in the same change — see the sync checklist in `AGENTS.md`.

## Web frontend

Vanilla HTML/CSS/JS served from `web/` (no build step). The floor is a
canvas-rendered conveyor with hand-authored pixel sprites (`web/js/sprites.js`):
a palette derived from AgentLaboratory's artwork (warm paper/cream, charcoal
ink, logo-red accent, amber/gold, dusty blue/teal/green), characters for every
station (Sorter, six specialists, Boss, Reporter, Archivist), document
envelopes tinted per doc class, stamps, bins, and conveyor rollers. The
station roster and doc-class colors must stay aligned with
`pipeline_schema.py` and the pipeline's `taxonomy.yaml`.
