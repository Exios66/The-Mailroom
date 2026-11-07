# Handoff

**From:** Browser QA / review fixes → **To:** M2 catch-up implementation

Completed source steps:
- M0: The-Mailroom #63 and llm-mailroom #166 merged.
- M1: producer contract #165 and consumer #64 merged. Source registry and
  conformance kit support primary Phoenix/Langfuse and conformant plugins.
- PR #66: browser-audit fixes plus review follow-ups; no merge performed.
- M2 A-7: adopt producer main `65523a220954d05bdf9b3d6604eb2fe128342f58`
  (0.9.1), vendor its exact contract bytes with `matches_pin=true`, align the
  optional eval engine to Dojo 0.27.2 at `1cd4aba76d82eea20c6e8dfcc0d760881bf84924`.
  The vendor script now preserves fetched bytes and has a regression check.

Owner action: confirm CircleCI is enabled for Exios66/The-Mailroom. Do not mark
M1's CI exit criterion complete without that evidence.

Next bounded source step: A-4, a dedicated classification-arbiter stage across
models, interpreter, routing path and surfaces. Keep the generated contract
producer-owned. A-5 can read existing span output until pipeline gate telemetry
lands. A-8 should surface all unmapped spans.

Pipeline prerequisites remain T-1/T-2/T-3 (schema and multi-sink emission) and B-*
(document events). T-6/F-3 consume their emitted golden traces; do not invent
upstream trace attributes or a new local scoring implementation here.

Backend requirement: Observatory works with whatever conformant trace adapters
are configured. Phoenix and Langfuse are primary, not mandatory. New sinks use
`mailroom.sources` plus `tests/source_conformance.py`; never hardcode a required
Langfuse service or fall back to fabricated/stale live rows.
