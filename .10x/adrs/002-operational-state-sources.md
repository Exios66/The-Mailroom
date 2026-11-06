# ADR-002: Operational state: traces for document events, producer HTTP for process state

**Status:** Accepted (2026-11-06)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit

## Context
The extraction gate, Gmail triage lane, decision review, relations, ops monitor, watchdog and pager write nothing to Langfuse. The visualizer's rule is "Langfuse is the sole source".

## Decision (recommended 2a)
Document-scoped events (gate, triage lane, decision review) are emitted to Langfuse by the pipeline. Process-scoped state (watchdog, pager on/off, ops monitor, queue depth, relations mode) is read from the producer's existing read-only HTTP endpoints through the backend proxy. It is labelled as live producer state, never mixed into run data, and never cached as if it were trace history.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| 2b All through Langfuse (synthetic ops traces) | One source | Heartbeat noise in the trace store and cost | Pollutes the trace data |
| 2c Don't show ops state | Purity | Operators keep using the CLI | Leaves the S2 gap |

## Consequences
- Amends the "sole source" rule to: sole source of *run* data.
- Risk: public exposure, mitigated by server-side field classification (G-1).
