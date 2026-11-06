# The-Mailroom: alignment, UI, graphics, visual design and deployment plan

**Status:** Proposed. Waiting on the owner's decisions (section 9).
**Date:** 2026-11-06
**Feature slug:** `mailroom-alignment-audit`
**Repos:** The-Mailroom (visualizer, v0.5.1 @ `cab7a41`) and llm-mailroom (pipeline, v0.9.1 + Unreleased @ `da07cc2`)
**Author:** 10x-Team (all 12 roles)

---

## 1. Summary

The-Mailroom shows an older version of the pipeline. Its producer pin, `1a1ec3d` from Oct 25, is 80 commits behind pipeline `main`. Its topology mirror says it is based on `959bb0b`. The pipeline has also added nodes, agents and whole subsystems that the visualizer cannot see. The pipeline is still changing: its roadmap (unified audit row, stage 2) adds a scoring node family and an `audit_failed` terminal before the end of stage 2.

The root cause is structural. Alignment depends on people copying constants by hand into `pipeline_schema.py`, `trace_interpreter.py` and test fixtures. Nothing checks those copies, so drift never shows up as a failing test.

The plan has four parts:

1. **Make drift fail loudly.** The pipeline publishes a machine-readable contract, and the visualizer tests itself against it (workstream A).
2. **Catch up once** to pipeline `main` and v0.9.1 (workstream A).
3. **Redraw the floor and the Observatory from the contract** instead of hard-coded station lists, on one shared design system (workstreams C and D).
4. **Fix the deployment and CI gaps.** The most urgent is the pipeline's Railway config, which stops being honoured on **2026-12-01** (workstream H).

Recommended order: A → H (urgent part) → F → E → D → C → G/I in parallel. The total is about 17–23 working days of focused work, plus cross-repo pipeline tasks of about 4–6 days.

---

## 2. Audit findings

Severity: **S1** means the display is wrong or a deadline is near. **S2** means a feature or signal is missing. **S3** means quality or maintainability.

### 2.1 Pipeline alignment (Architect, Staff Engineer)

| # | Finding | Evidence | Effect | Sev |
|---|---|---|---|---|
| A1 | Graph node `classification_arbiter` (span `arbitrate-classification`, type `agent`) is not mirrored | `build_graph.py:3161`; missing from `SPAN_STAGE_MAP`, `NODE_OBSERVATION_TYPES`, `Stage`, `NODE_ORDER` | Parked classifications fall through to the `unknown` stage | S1 |
| A2 | Extraction gate (v0.9.1, `agents.extraction_gate`, state `extraction_gate`, `extracted` audit entry) is not modelled | pipeline CHANGELOG v0.9.1 | Gate verdicts are invisible | S2 |
| A3 | Agents `gmail_triage` and `relations` are missing from `AGENTS` | `taxonomy.yaml: agents` | Not shown on the roster or prompts view | S2 |
| A4 | The free Gmail triage lane (`_run_triage_lane`) runs outside the graph | flowchart.md "Entry points" | Emails handled by triage never appear on the floor | S2 |
| A5 | Producer pin claims disagree: code and README say `1a1ec3d`, the CHANGELOG says `4c274a4`, schema comments say `959bb0b` | grep across 9 files | Nobody can tell which pipeline version is mirrored | S2 |
| A6 | Eval uses an interim Dojo build (`718e326`, after 0.24.2); the pipeline is on Dojo v0.27.2 | pyproject vs pipeline CHANGELOG | Offline eval scores can differ from the pipeline's own scores | S2 |
| A7 | Subclass catalogs cite Dojo v0.16.0; the pipeline now uses the `sorter_v15` prompt and the Dojo sorter guide (`certificate_of_formation` dropped, new correspondence precedence) | `pipeline_schema.py:362` | Subclass labels and filters may be stale | S3 |
| A8 | The pipeline roadmap's next changes (scoring node family `score_common` and `score_<type>`, `audit_failed`, unified audit row `/audit` shape) will break the visualizer again | `unified-audit-row/stage-4` task F1 | Drift starts again as soon as stage 2 lands | S1 (forward) |
| A9 | Confirmed bug: `ui/src/components/AuditChain.tsx` reads `action`/`hash`/`id`, but the API returns `event`/`entry_hash`/`entry_id` | AuditChain.tsx:42,51,57 | The audit chain shows "event" and "—" | S1 |
| A10 | No machine check exists between the two repos; test fixtures are written by hand | `tests/fake_langfuse.py` | Drift passes CI | S1 |

### 2.2 Telemetry gaps in the pipeline (cross-repo)

These subsystems write **nothing to Langfuse**, so under the "Langfuse is the sole source" rule the visualizer cannot show them:

| Subsystem | File | Data available today |
|---|---|---|
| Extraction gate | `agents/extraction_gate.py` | State and audit entry only |
| Gmail intake and triage lane | `pipeline/gmail_intake.py`, `agents/gmail_triage.py` | None traced |
| Decision review | `pipeline/decision_review.py` | None traced |
| Relations clerk and scan | `pipeline/relations*.py` | HTTP `GET /matters/{id}`, `/api/relations/mode` |
| Ops monitor, watchdog, pager | `pipeline/ops_monitor.py`, `watchdog.py`, `pager.py` | HTTP `GET /ops/status`, `/health`, `/queue` |
| LiteLLM gateway tiers and Modal GPU, free-model swarm | `taxonomy.yaml: gateway, free_model_swarm` | Generations carry the model name only |

### 2.3 UI, display and graphics (Product Manager, Senior Engineer)

| # | Finding | Sev |
|---|---|---|
| U1 | The floor (`web/js/floor.js`) hard-codes 7 stations with fixed pixel `x` values (SORTER … REVIEW). The pipeline has 14 graph nodes, retry loops, two arbiters, a judge gate, a triage lane and post-terminal side effects. Retries and arbiters are folded into neighbouring stations, so the routing a document actually took is not visible. | S1 |
| U2 | Six surfaces (`web/`, `hosted/`, `ui/`, `tui/`, `terminal/`, `operator_desk/`) each re-implement stage colours, document-class stamps and labels. A pipeline change must be repeated 4+ times. | S2 |
| U3 | 89 distinct hex colours in use. `theme.css` has 19 custom properties, `app.css` 43 and `index.css` 39, with no shared source. | S3 |
| U4 | Accessibility: the pixel console has 1 `aria-` attribute across its HTML and JS, no `prefers-reduced-motion` and no keyboard route to envelopes on the canvas. The Observatory is better (23 in its HTML). Floor labels are low-contrast (see `docs/screenshots/floor.png`). | S2 |
| U5 | The canvas floor is fixed-width: the screenshot shows it clipped on the left at 1920 px. It is not usable on phones. | S2 |
| U6 | There is no in-product "what pipeline version am I looking at" indicator, and no staleness warning when traces carry span names the visualizer doesn't know. | S2 |
| U7 | The Observatory review queue is a dense table; the resolve form takes about 400 px per row (`observatory-pipeline.png`). | S3 |
| U8 | Screenshots in `docs/screenshots` predate v0.9.1, so the README shows an out-of-date product. | S3 |

### 2.4 Quality (QA)

| # | Finding | Sev |
|---|---|---|
| Q1 | Baseline: 532 pass, 2 skipped, 1 fail. `test_dmr091_regressions::test_reconnect_retains_outage_and_last_success_timestamp` fails because `asyncio_mode = "auto"` is configured but pytest-asyncio is not in `[dev]`. | S2 |
| Q2 | No test runs the interpreter against real current pipeline output | S1 |
| Q3 | The frontend has no automated check at all (the AGENTS.md policy is "verify manually"), so A9 and U5 shipped unnoticed. | S2 |

### 2.5 Security

| # | Finding | Sev |
|---|---|---|
| X1 | Adding ops, relations and matter panels to the **public** `/live` Observatory could expose matter IDs, filenames or operator phone numbers (pager). Each new field needs a public/operator classification. | S2 (forward) |
| X2 | `ui/` npm tree: Dependabot bumps are merged but `npm audit` is not run anywhere. | S3 |
| X3 | Test JWT key is 20 bytes (InsecureKeyLengthWarning). Test-only, but worth fixing so the warning can't hide a real one. | S3 |
| X4 | The operator auth posture (DMR-111/113) is solid; keep it unchanged. | — |

### 2.6 Deployment and operations (DevOps, SRE)

| # | Finding | Sev |
|---|---|---|
| D1 | **The pipeline still deploys from `railway.json`. Railway stops honouring Config as Code on 2026-12-01.** The visualizer's `.railway/railway.py` only `preserve()`s the producer service. | **S1, deadline in 25 days** |
| D2 | The-Mailroom has no CI. The pipeline uses CircleCI, and GitHub Actions is not available on this account. | S2 |
| D3 | Pin bumps touch 9 files by hand. The pipeline already has `bump_dojo_scoring.py`; there is no equivalent here. | S3 |
| D4 | The HF Space and gh-pages snapshot are published by hand. Their freshness against `main` is checked only by `publish_pages.sh --status`. | S3 |
| D5 | No SLO or alert covers floor freshness or contract drift. The poller retains the last good snapshot (DMR-091), but nobody is told when it goes stale. | S3 |

---

## 3. Goals and non-goals

**Goals**
1. Every node, span, agent, document class, failure class and score the pipeline emits at the pinned SHA is shown correctly. Anything unknown is flagged visibly, never silently.
2. Pipeline changes that break the visualizer fail CI in the visualizer, and, if the owner chooses, also in the pipeline.
3. The floor shows the real route a document took, including retries, the classification arbiter, the judge/arbiter loop, the extraction gate and review/failure sidings.
4. One design system (tokens and palette) is shared by every surface.
5. The deployment gaps (D1, D2) are closed before 2026-12-01.

**Non-goals**
- Replacing Langfuse as the source of truth for document runs.
- Adding a Node toolchain to `web/` or `hosted/`. Both stay vanilla.
- Rewriting the operator auth stack.
- Building new pipeline features; pipeline changes are limited to telemetry and contract export.

---

## 4. Approaches considered (CTO, Architect)

| Option | Summary | Pros | Cons |
|---|---|---|---|
| **1. Contract export and data-driven UI (recommended)** | The pipeline writes `mailroom-contract.json` (nodes, edges, spans→obs types, agents, classes, subclasses, failure classes, score names, thresholds) from its own constants. The visualizer vendors it at the pinned SHA, tests against it, and draws the floor from it. | Drift becomes a test failure. New nodes (the scoring family) appear with zero visualizer code. One source for every surface. | Needs a small pipeline PR plus a schema version. The floor layout engine is real work. |
| 2. Resync by hand again, then add a drift test | Copy constants as before; add a test that imports the pinned pipeline and compares. | Smallest change | The test needs heavy pipeline deps (structlog and others) in visualizer CI. Still a hand copy. Breaks again at stage 2 of the pipeline roadmap. |
| 3. Import the pipeline directly at runtime | Drop the mirror; `import graph.routing` etc. | No copy at all | Breaks the "never import pipeline internals from the display path" rule and the light `[dev]` install. The HF Space image grows. Rejected. |
| 4. Don't build: freeze the visualizer, point users at Langfuse dashboards | — | Zero effort | Loses review resolve, the floor, and the public Observatory. Rejected. |

---

## 5. Target design

### 5.1 Contract (ADR-001)

- **Producer side (llm-mailroom):** `src/scripts/export_contract.py` builds `contract/mailroom-contract.json` from the live constants: `build_graph` nodes and edges (introspected from the compiled LangGraph), `NODE_OBSERVATION_TYPES`, `taxonomy.yaml` (`doc_classes`, `agents`, `confidence`), `failures.py`, the score names used in `observability/*`, and the Dojo subclass inventories. It carries `contract_version` (semver) and `pipeline_sha`. A CircleCI check fails if the committed file is stale.
- **Consumer side (The-Mailroom):** `mailroom_ui/contract/mailroom-contract.json` is vendored at the pinned SHA by `scripts/bump_producer_pin.py`, which moves all 9 pin locations in one go (D3). `pipeline_schema.py` loads it and keeps only *display* data: labels, colours and sprites. The source-of-truth rule is unchanged, because the contract describes the trace shape and contains no run data.
- **Unknown handling:** a span not in the contract renders as a visible "UNMAPPED: <name>" station chip, increments `/api/health.unmapped_spans`, and logs once (U6).

### 5.2 Operational state (ADR-002), owner decision required

Option **2a (recommended):** the pipeline emits Langfuse telemetry for document-level events it currently drops: the extraction gate as an `event` plus a `extraction_gate` categorical score, the triage lane as its own `document-pipeline` trace with tag `lane-triage`, and decision review as a `span`. These are per-document, so they belong in traces.
For **process-level** state (watchdog, pager, ops monitor, relations mode, queue depth), which is not per-document, the visualizer reads the producer's existing read-only HTTP (`/ops/status`, `/queue`, `/health`, `/api/relations/mode`) through the backend proxy it already has (`pipeline_ops.py`). These panels are labelled "producer live state, not trace data".
Option 2b: everything goes through Langfuse, including synthetic ops traces. That is purer, but it puts heartbeat noise into the trace store.
Option 2c: don't show ops state.

### 5.3 Surfaces (ADR-003), owner decision required

| Surface | Proposed role | Action |
|---|---|---|
| `hosted/` Observatory `/live` | **Primary** public and operator desk | Full parity with the contract; new Pipeline map view |
| `web/` pixel console | Signature live floor (the brand) | Data-driven floor redraw |
| `tui/` | Operator CLI | Contract parity for labels and stages only |
| `terminal/` (gh-pages) | Static showcase | Snapshot refresh only |
| `operator_desk/` | Backend module, not a surface | No visual work |
| `ui/` React desk | **Freeze** (recommended) or retire | Fix A9 only; mark "maintenance mode" |

### 5.4 Design system and graphics (ADR-004)

- One source file, `design/tokens.json`: stage, phase, document-class, verdict, failure-class and severity palettes, type scale and spacing. `scripts/build_tokens.py` (Python, no npm) generates `web/css/tokens.css`, `hosted/css/tokens.css`, `ui/src/tokens.css` and `tui/theme.py` (Rich styles). Each surface's existing CSS swaps its literals for `var(--…)`.
- Palette rules: every categorical colour passes 3:1 against both the dark floor and the light Observatory background. The stage palette stays distinguishable under deuteranopia and protanopia (checked by a Python validator in the test suite). Colour never carries meaning alone; each station also has a glyph and a label.
- **Floor v2 (pixel console):**
  - The layout is computed from the contract graph in three lanes: **Intake and sort** (intake → classify ↻ retry → review-classify → classification arbiter), **Extract and adjudicate** (extract ↻ retry → gate badge → judge ⇄ arbiter, boss), and **Report and archive** (report → *scoring family, when present* → catalog → archive). The review siding and the failed siding sit underneath. A triage side-lane enters from the inbox.
  - Envelopes trace their actual `routing_path`. Loops are drawn as a curved return track with a counter badge (×2), so retries are visible rather than folded in.
  - New sprites: classification arbiter (gavel on a sorting desk), extraction gate (turnstile; green, amber or red lamp), judge ⇄ arbiter shuttle, scoring bench (reserved for M6 of the pipeline), Gmail triage chute.
  - The canvas scales to fit its container (`devicePixelRatio`-aware), uses integer scaling to keep pixels crisp, and falls back to a vertical lane layout under 720 px.
  - `prefers-reduced-motion`: envelopes jump between stations instead of animating. An off-canvas, keyboard-focusable list mirrors the envelopes so screen readers and keyboard users can open the inspector.
- **Observatory:**
  - A new **Pipeline map** tab draws the contract graph as an SVG (the same mermaid topology as the pipeline's `flowchart.md`, laid out by the backend). Live per-node counts and p95 latency are overlaid, and an edge lights up when a run takes it.
  - The review queue moves to a card layout with a collapsible resolve drawer (U7).
  - A header **version strip** shows the pipeline SHA and version, the contract version, the Dojo version and the unmapped-span count (U6).
- **Inspector additions** (both surfaces): extraction gate verdict chip, classification-arbiter decision, judge pass count, retry counters, tier and model (gateway tier from the generation model alias), and failure-class chip.
- **Screenshots and README:** regenerated by a Playwright script (Python) from a seeded `demo` environment, at deviceScaleFactor 2 (U8).

---

## 6. Workstreams

Each task is no longer than half a day unless marked. Owner roles are in brackets.

### A. Contract and catch-up [Architect, Staff Engineer, SDE]
- A-1 (pipeline) Write `export_contract.py`, commit `contract/mailroom-contract.json`, add a CircleCI staleness check. *1.5 d*
- A-2 Add `scripts/bump_producer_pin.py`, which moves the SHA in all 9 locations and vendors the contract. Fix the A5 provenance disagreement. *0.5 d*
- A-3 Make `pipeline_schema.py` load stages, observation types, agents, classes, subclasses and failure classes from the contract; keep display metadata local. *1.5 d*
- A-4 Add the `classification_arbiter` stage end to end (models, interpreter, routing path, phases). *0.5 d*
- A-5 Model the extraction gate (interpreter reads the event or score once A-1/B-1 exist; until then reads `extraction_gate` from the span output when present). *0.5 d*
- A-6 Roster: `gmail_triage`, `relations`; regenerate `prompt_registry.py`. *0.5 d*
- A-7 Bump the pin to the then-current pipeline `main` (v0.9.1 or later); align the `[eval]` Dojo pin to v0.27.2 and rerun the eval goldens. *0.5 d*
- A-8 Add unmapped-span handling and the health counter. *0.5 d*
- A-9 Fix A9 (`AuditChain.tsx` fields), with the nesting by `kind`/`parent_id` from pipeline task F1 behind a feature check. *0.5 d*

### B. Pipeline telemetry (cross-repo, llm-mailroom) [Architect, SDE]
- B-1 Extraction gate → Langfuse event plus categorical score. *0.5 d*
- B-2 Triage lane → its own trace with `lane-triage` tag and `triage-email` span. *1 d*
- B-3 Decision review → span. *0.5 d*
- B-4 Add the new names to `NODE_OBSERVATION_TYPES` and the contract. *included*

### C. Information architecture and surfaces [CTO, Product Manager]
- C-1 Record the surface roles (ADR-003) and put `ui/` into maintenance mode (README banner, `/desk` footer). *0.5 d*
- C-2 Observatory navigation: add the Pipeline map tab; group Debug under an operator-only menu. *0.5 d*

### D. Design system and graphics [Senior Engineer, SDE, QA for a11y]
- D-1 `design/tokens.json`, `build_tokens.py`, palette validator test. *1 d*
- D-2 Migrate `web/`, `hosted/`, `ui/` and `tui/` to the tokens. *1.5 d*
- D-3 Floor v2 layout engine (contract graph → lanes; loops as return tracks). *2.5 d*
- D-4 New sprites (5) and station glyphs. *1.5 d*
- D-5 Responsive canvas, reduced motion, keyboard and screen-reader envelope list. *1 d*
- D-6 Observatory Pipeline map (backend layout + SVG + live overlay). *2 d*
- D-7 Review-queue cards and the version strip. *1 d*
- D-8 Inspector additions across both surfaces and the TUI. *1 d*

### E. Ops and relations panels (only if ADR-002 option 2a or 2b is chosen) [SDE, Security]
- E-1 Producer live-state panel (watchdog, ops monitor, queue depth, pager on/off with no numbers). *1 d*
- E-2 Relations mode and matter graph (operator-only). *1 d*

### F. Quality [QA]
- F-1 Add `pytest-asyncio` to `[dev]` (fixes Q1). *0.1 d*
- F-2 Contract conformance tests: every contract node has a stage, colour, glyph and phase; every score name has a reader. *0.5 d*
- F-3 Golden traces: record one sanitized real run per class (and one per review and failure route) from the pipeline's `mailroom-fixtures` mock experiment; store them as JSON and run the interpreter against them. *1 d*
- F-4 Browser smoke checks in Python with Playwright (already installed): boot the server against the fake source, load every screen, assert no console errors, take screenshots at 1440 px and 390 px. **This changes the AGENTS.md "verify manually" policy, so it needs the owner's approval.** *1 d*

### G. Security [Security Engineer]
- G-1 Field-level public/operator classification for every new panel and field; enforce it in the backend serializer, not the client. *0.5 d*
- G-2 `npm audit` in CI for `ui/`; 32-byte test JWT key. *0.25 d*
- G-3 Threat-model review of the read-only producer proxy (SSRF via `MAILROOM_PIPELINE_URL`, token scope). *0.5 d*

### H. Deployment and CI [DevOps]
- **H-1 (urgent, pipeline repo) Move llm-mailroom from `railway.json` to Railway IaC before 2026-12-01.** Either the pipeline gets its own `.railway/railway.py`, or the visualizer's IaC (which already declares both services) owns both: owner decision. *1 d*
- H-2 CircleCI for The-Mailroom: pytest, contract staleness against the pin, token build check, Playwright smoke (if F-4 is approved), `npm audit`. *1 d*
- H-3 Release v0.6.0 (alignment) and then **v1.0.0** (floor v2 is a visual-design break, which AGENTS.md says is MAJOR). Refresh the HF Space, gh-pages and the Digital-Mailroom import. *0.5 d each*

### I. Reliability [SRE]
- I-1 SLOs: floor snapshot age < 2 × `MAILROOM_POLL_INTERVAL` for 99% of minutes; unmapped spans = 0. Expose both on `/api/health`. *0.5 d*
- I-2 Visible "stale" banner when the snapshot age goes over the SLO; runbook in `docs/deployment.md` (Langfuse down, producer down, contract mismatch). *0.5 d*

---

## 7. Sequencing and milestones (Engineering Manager)

| Milestone | Contents | Est. | Exit criteria |
|---|---|---|---|
| **M0 Stop the bleeding** | F-1, A-9, H-1 | 1.5 d | Suite green; audit chain correct; pipeline deploys under IaC |
| **M1 Contract** | A-1, A-2, A-3, F-2, H-2 | 5 d | CI fails on a deliberately renamed span |
| **M2 Catch-up** | A-4–A-8, B-1–B-4, F-3 | 5 d | Golden traces for every route render with zero unmapped spans; release v0.6.0 |
| **M3 Design system** | D-1, D-2, G-2 | 3 d | One token source; palette validator green |
| **M4 Floor v2 and Observatory map** | D-3–D-8, C-1, C-2, F-4, I-1, I-2 | 10–12 d | Screenshots at 1440 px and 390 px; keyboard path to the inspector; release v1.0.0 |
| **M5 Ops panels (optional)** | E-1, E-2, G-1, G-3 | 3 d | Public `/live` shows no operator-only field (tested) |

Dependencies: M1 needs the A-1 pipeline PR merged. M2's B tasks are pipeline PRs. The pipeline's own roadmap stage 2 (scoring nodes) should land after M1, so the scoring stations arrive through the contract with no extra visualizer work. That also completes the pipeline's task F1.

---

## 8. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| The pipeline graph changes during M2–M4 (roadmap stage 2) | High | Contract-driven layout; pin bump is one command |
| LangGraph introspection is unstable across versions | Medium | The exporter falls back to an explicit node and edge list tested against `build_graph` |
| Floor v2 scope creep (sprites, animation) | Medium | Fixed sprite list (5); ship the layout first with placeholder glyphs |
| Railway IaC is still beta (`railway_sdk`) | Medium | Keep `railway.json` until IaC deploys are verified; do a dry `railway config plan` first |
| Public exposure of ops data | Low–Med | G-1 server-side classification, with tests |
| Digital-Mailroom hub drift after the v1.0.0 import | Medium | Import immediately after each release, as AGENTS.md requires |

---

## 9. Decisions needed from the owner

1. **Contract approach:** option 1 (generated contract, recommended) or option 2 (hand resync and a drift test)?
2. **Operational state (ADR-002):** 2a (traces for document events, producer HTTP for process state; recommended), 2b (all Langfuse) or 2c (don't show)?
3. **Surface roles (ADR-003):** is the Observatory primary? Freeze or retire the React desk?
4. **Browser checks (F-4):** allow Python Playwright smoke tests, which changes the "verify manually" policy?
5. **Railway (H-1):** who owns the producer's IaC, the pipeline repo or the visualizer's two-service file?
6. **Versioning:** ship floor v2 as v1.0.0?
7. **Scope:** all of M0–M5, or M0–M4 with M5 deferred?

---

## 10. Proposed ADRs

Drafts in `.10x/adrs/`, all marked **Proposed**:
- ADR-001 Generated pipeline contract as the alignment mechanism
- ADR-002 Operational state: traces for document events, producer HTTP for process state
- ADR-003 Surface roles and React desk maintenance mode
- ADR-004 Shared design tokens generated in Python
