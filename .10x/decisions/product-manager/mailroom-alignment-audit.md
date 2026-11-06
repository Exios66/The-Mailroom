# Product Manager — mailroom-alignment-audit

Status: **Approved** 2026-11-06. Spec `.10x/specs/2026-11-06-mailroom-alignment-audit-design.md`.

## User stories
1. As an operator, I resolve REVIEW items in one Observatory tab with the source, the extraction, the reason it was parked, and the audit chain side by side.
2. As a viewer, I watch the floor and see the exact route each document took, including retries, arbiters, the judge loop and the gate.
3. As a maintainer, I bump the pipeline pin with one command, and CI tells me what no longer matches.
4. As an operator, I see which pipeline, contract and Dojo versions the display is showing, and whether the data is stale.

## Success criteria
1. Zero unmapped spans on golden traces for every route at the pinned SHA.
2. A renamed pipeline span fails visualizer CI.
3. The floor shows retries, both arbiters, the judge loop and the gate.
4. One token source; categorical colours ≥ 3:1 contrast.
5. No Railway config in either repo; the HF Space pair serves the hosted desk.
6. The review desk tab supports resume, record, requeue and complete, with validated extraction edits.

## Scope
All of M0–M5.
