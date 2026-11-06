# ADR-006: Document traces are the displayed events, on any trace backend

**Status:** Accepted (2026-11-06, owner direction)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit
**Supersedes:** the Langfuse-specific mechanism in ADR-002 (process-level status over producer HTTP is unchanged)

## Context
The owner's rule: what the visualizer displays are **document traces**, whatever backend stores them. Langfuse and Phoenix are the primary sinks, and the wiring must work across trace backends in general.

What the code does today:
- **Pipeline:** `observability.tracing` picks **one** provider. `pipeline_trace`, `observation` and `traced_node` emit only for Langfuse or Braintrust. With Phoenix selected, the pipeline sends only OpenInference-instrumented OpenAI calls: no `document-pipeline` root, no node spans, no stage output. A Phoenix-only deployment therefore cannot drive the floor.
- **Visualizer:** the `TraceSource` protocol (`mailroom_ui/sources.py`) is already backend-neutral, with `LangfuseSource`, `PhoenixSource` and the `MultiSource` fan-out. But `MAILROOM_SOURCE` only knows `langfuse|phoenix|both`, there is no adapter registry, and each adapter normalises shapes its own way.

## Decision
1. **The contract defines the document-trace schema** (ADR-001 gains a `trace_schema` section): the root trace name; node and event span names; each span's kind (chain, agent, evaluator, retriever, generation, span); and the attribute keys a run carries (`mailroom.stage`, `mailroom.doc_id`, `mailroom.doc_type`, `mailroom.doc_subclass`, the confidences, `mailroom.failure_class`, `mailroom.gate.*`, `mailroom.review.*`, matter/session, environment, release). The schema is the interface; no backend's data model is.
2. **The pipeline emits document traces through a sink-neutral layer to every configured sink.**
   - `OBSERVABILITY_PROVIDER` accepts a list (for example `langfuse,phoenix`).
   - The canonical emission is OpenTelemetry spans that follow the trace schema.
   - Phoenix and any OTLP backend receive them through OTLP exporters, with span kinds mapped to OpenInference kinds.
   - Langfuse receives the same document events through its SDK (OTel-based in v4) and keeps its native features: scores, prompt linking, sessions.
   - Anything a viewer needs is also carried as span attributes, so non-Langfuse sinks lose nothing displayable.
   - Document events (extraction gate, triage lane, decision review, classification arbiter) are spans and attributes in this layer, never Langfuse-only scores.
3. **The visualizer reads document traces from any registered source.**
   - `MAILROOM_SOURCE` becomes a list (`langfuse,phoenix,...`). Adapters register by name in a source registry.
   - Every adapter normalises into the same trace-schema shape before `trace_interpreter` sees it.
   - A **source conformance kit** feeds one golden document trace through each adapter's fake backend and requires the same `PipelineRun`. Adding a backend means writing an adapter that passes the kit.
4. **Process-level state** (watchdog, pager, ops monitor, queue depth) is not a document trace. It stays on the producer's read-only HTTP, labelled as live producer state (ADR-002, unchanged).

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Langfuse as the only displayed sink (the ADR-002 wording) | Simplest | Phoenix and other backends can't drive the display | Contradicts the owner's direction |
| Per-backend adapters in the pipeline with no shared schema | Reuses existing setup modules | Every backend drifts separately; the visualizer must special-case each | That is the drift problem again |
| Pure OTLP everywhere, dropping the native Langfuse SDK | One code path | Loses Langfuse scores, prompt linking and score configs the pipeline relies on | Too much loss for now; can be revisited |

## Consequences
### Positive
- Any OTLP-capable backend (Phoenix, Tempo/Jaeger via a new adapter, etc.) can serve the floor.
- Langfuse and Phoenix carry the same document events; the visualizer can merge or fail over between them.
### Negative
- The pipeline's tracing layer becomes multi-sink: more code and more tests.
- Scores are duplicated as attributes for non-Langfuse sinks.
### Risks
- **Double emission cost and latency.** Mitigation: batching exporters and the existing per-node `flush()` policy, which is applied per sink.
- **Attribute-name drift.** Mitigation: the names live in the contract; the pipeline tests that every emitted attribute is in the schema, and the visualizer's conformance kit tests that it reads them.

## Dependencies
- ADR-001 (contract carries `trace_schema`).
- Constrains the B workstream (telemetry): all new events go through the neutral layer.
