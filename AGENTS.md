# AGENTS.md — The-Mailroom

The-Mailroom is the **visual engine** for the `llm-mailroom` multi-agent legal-document pipeline: a pixel-art console (web + planned TUI) that renders every run from its Langfuse traces. **Langfuse is the sole source of truth** — every displayed value is derived from Langfuse traces, observations, scores, and sessions. This repo never fabricates or falls back to locally-canned data. Python 3.11+, no build step.

## Sister repo: `llm-mailroom` (the pipeline)

- **Expected location**: a sibling of this repo, i.e. `../llm-mailroom` from this checkout (e.g. `/Users/luciusjmorningstar/Downloads/llm-mailroom`). It is **not currently present on this machine** — clone it before relying on `MAILROOM_TAXONOMY`.
- It is the **upstream**: The-Mailroom reads *its* Langfuse project (US cloud, project `llm-mailroom`). Its `AGENTS.md` is authoritative for pipeline internals; consult it whenever the pipeline's tracing contract is in doubt.
- **What we mirror from it, and must keep in sync (the #1 maintenance duty)** — when the pipeline changes, update all of these in one change:
  - `mailroom_ui/pipeline_schema.py` — mirrors `graph/routing.py` + `config/taxonomy.yaml`: node/span names (`SPAN_STAGE_MAP`), stage→phase map, agent roster, `DOC_CLASSES`, `SPECIALIST_BY_DOC_CLASS`, confidence thresholds.
  - `mailroom_ui/trace_interpreter.py` — maps its span names, trace metadata/input/output fields, and score names (`JUDGE_VERDICT_SCORES` = `mailroom-pipeline-judge`, `JUDGE_QUALITY_SCORES` = `mailroom-pipeline-quality`).
  - `web/js/sprites.js` — `DOC_TYPE_COLORS` keys must match `doc_classes` keys.
  - Tests — `tests/fake_langfuse.py` fixtures mirror the trace contract.
  - CHANGELOG entry for the sync (see Release process).
- **Live override**: `MAILROOM_TAXONOMY` env var → absolute path to llm-mailroom's `config/taxonomy.yaml`. When set, thresholds/doc classes are read from there instead of the bundled mirror (`PipelineSchema.load()`). Requires a restart — config is cached at process level.
- **Breakage map** (what happens here if the pipeline changes): new span name → run interpreted as `unknown` stage; new doc class → envelope falls back to the gray default stamp color; renamed judge scores → verdict/quality vanish from runs; new env/tag → filters in `.env` may need updating.

## Commands

```bash
pip install -e ".[dev]"        # install (deps NOT vendored; no venv in repo)
python -m pytest tests/ -q     # whole suite (never hits real Langfuse)
python -m server.main          # FastAPI web server on :8001 (also: mailroom-web)
mailroom-tui                   # TUI console (planned, M4)
python scripts/seed_demo.py    # seed demo traces INTO Langfuse (planned, M5)
python scripts/release.py --help     # semver release workflow (see below)
```

- Tests: `pytest tests/ -v`; coverage via `--cov=. --cov-report=html`.
- **No linter, formatter, or typechecker is configured — don't invent one.**
- Frontend is **vanilla HTML/CSS/JS with no build step and no npm** — never introduce a Node toolchain.
- Config lives in `.env` (see `.env.example`); copy `.env.example` → `.env` and add `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`.

## Architecture (not obvious from filenames)

- `mailroom_ui/` — data core (everything reads Langfuse only):
  - `langfuse_source.py` — Langfuse SDK adapter: `client.api.trace.list/get`, `client.api.observations.get_many`, `client.api.scores.get_many`, `client.api.sessions.list/get`; `TTLCache`; `LangfuseUnavailable`. `list_recent_runs()` uses trace-list responses only (cheap "light" runs for the floor); `get_run()` fetches observations+scores for drill-down.
  - `trace_interpreter.py` — `interpret_trace(trace, observations?, scores?)` → `PipelineRun`. Accepts **both v2/v3 snake_case and v4 camelCase** observation shapes (see SDK tolerance). Light runs (no observations arg) have empty span/generation detail. Re-run clustering: deterministic trace ids are reused by pilot/attempt re-runs, so a trace can carry several full runs — observations are clustered by time gaps (`RUN_GAP_S`) and only the latest cluster is kept.
  - `pipeline_schema.py` — topology mirror (see sister-repo section).
  - `models.py` — pydantic: `PipelineRun`, `NodeSpan`, `Generation`, `Score`, `SessionSummary`, `Metrics`, `Stage`, `Phase`.
  - `metrics.py` — `compute_metrics()` aggregations (counts by stage/verdict, cost, tokens, p95 generation latency, per-doc-type).
- `server/` — FastAPI, read-only:
  - `main.py` — `/api/health`, `/api/traces[?since&limit&stage&environment]`, `/api/traces/{id}` (full), `/api/metrics`, `/api/sessions[/{id}]`, `/api/review-queue`, `/api/meta`, WebSocket `/ws`; mounts `web/` at `/static` and serves `index.html` at `/`. Browser never holds Langfuse keys — the backend proxies everything.
  - `poller.py` — `PollHub`: background poll loop → compact `floor_payload` snapshots broadcast to all WS clients; full detail cached per trace with `detail_ttl`.
- `web/` — pixel-art SPA:
  - `js/sprites.js` — hand-authored pixel matrices + `PALETTE` (derived from AgentLaboratory media analysis: warm paper/cream, charcoal ink, logo-red accent, amber/gold, dusty blue/teal/green). **This is the craft centerpiece** — keep the style coherent: ink outline (`k`), 3-value shading per material, consistent light source, symmetric faces. Validate any sprite edit (uniform row width, known palette keys).
  - `js/floor.js` — canvas conveyor renderer (stations, rollers, envelope animation, review/failed sidings). `js/api.js` (fetch + WS with reconnect), `js/inspector.js`, `js/sessions.js`, `js/metrics.js`, `js/console.js`, `js/main.js` (app shell).
- `tui/` — planned rich-console (AgentLab-style `*** Beginning station: ... ***` banners, per-doc summary tables). Not yet built (M4).
- `scripts/seed_demo.py` — planned (M5): generates demo traces **into Langfuse** (env `demo`), never served directly.

## Langfuse is ALWAYS the source of visualization

- Every display value comes from Langfuse via the backend; no local JSON fallbacks anywhere in the display path.
- Demo/dev data is written **into** Langfuse (the seed script) so even development reads from Langfuse.
- When Langfuse is unreachable, the UI must show a "MAILROOM CLOSED — no Langfuse connection" state, not stale or canned data.

## Langfuse SDK version tolerance

- Works with `langfuse >= 2.50` through 4.x. **v4 returns camelCase at the observation level** (`startTime`, `endTime`, `modelId`, `totalTokens`, `inputTokens`, `outputTokens`, `totalCost`, trace `sessionId`/`updatedAt`); older SDKs and stored payloads use snake_case.
- Add new observation fields via `_both(d, "snake", "camel")` / `_pick(d, *keys)` in `trace_interpreter.py`; never assume a single case.
- **Every shape change needs both fixtures**: `tests/fake_langfuse.py` has `make_trace` (v2/v3 snake_case) and `make_trace_v4` (v4 camelCase); the interpreter must pass both.

## Trace structure we interpret (the contract with llm-mailroom)

- One `document-pipeline` trace per document; **deterministic trace id seeded from the filename**; re-runs reuse it (hence the cluster logic above).
- Verb-first node spans: `ingest-document`, `classify-document`, `extract-fields`, `route-for-review`, `adjudicate-conflict`, `compile-report`, `write-catalog`, `archive-document` (+ ingest variants `transcribe-pdf`, `extract-image-text`).
- `session_id = matter_id` (pilot runs use run-scoped sessions); tags `[mailroom, <env>, run-<n>, source-<corpus>?]`; metadata `{attempt, run_id, run_deadline}`; curated `input` (file metadata) / `output` (stage, doc_type, confidences, error).
- Scores: confidences (`classification_confidence`, `extraction_confidence`), run metrics (`estimated_cost_usd`, `total_tokens`, `stage_completed`, ...), judge verdict (`mailroom-pipeline-judge` = CORRECT/PARTIAL/MISS), quality (`mailroom-pipeline-quality` = 0–1).

## Config gotchas

- `.env` is loaded by `server/main.py:run()` via `load_dotenv()`; if you launch uvicorn directly (`uvicorn server.main:app`) you must export the vars yourself. `LangfuseSource` reads `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` (default `https://us.cloud.langfuse.com`).
- This repo uses **`LANGFUSE_HOST`** (SDK convention) while Langfuse docs/CLI use `LANGFUSE_BASE_URL` — if your shell exports `BASE_URL`, set `HOST` to match.
- All `MAILROOM_*` knobs (`MAILROOM_POLL_INTERVAL`, `MAILROOM_RECENT_WINDOW`, `MAILROOM_TRACE_LIMIT`, `MAILROOM_TRACE_TAGS`, `MAILROOM_TRACE_ENVIRONMENTS`, `MAILROOM_PORT`, `MAILROOM_TAXONOMY`, `MAILROOM_API_URL`) are documented in `.env.example`; poller/server read them at startup — restart to change.
- `pipeline_schema.py` is cached at process level — editing `taxonomy.yaml` or the mirror requires a restart.

## Testing quirks

- Tests never hit real Langfuse. `tests/fake_langfuse.py` provides `Obj`/`FakeClient`/`make_trace` (+ `make_trace_v4`); the source adapter accepts either the real SDK client or the fake.
- `tests/conftest.py` adds the repo root to `sys.path`; `asyncio_mode = "auto"` is set.
- Frontend has no test framework — verify manually (boot server, cycle all screens, inspect an envelope, disconnect Langfuse to see the closed state). Do not invent a JS test harness.

## Release process (semver + CHANGELOG + README + wiki + tags)

**Semantic versioning** (`MAJOR.MINOR.PATCH`), version lives in `pyproject.toml`:
- **MAJOR** — breaking change to the API responses, the data contract (trace interpretation), or the visual design.
- **MINOR** — new feature: new screen, new metrics, milestone delivery (M2/M3/M4/M5 each = MINOR).
- **PATCH** — bug fixes, docs fixes, tests-only changes.

**CHANGELOG.md** — Keep a Changelog format (https://keepachangelog.com). During development new entries accumulate under `## [Unreleased]`; on release they are moved under `## [X.Y.Z] - YYYY-MM-DD` with `Added`/`Changed`/`Fixed`/`Removed` bullets.

**Mandatory, in the same commit as the code, for every major update:**
1. Update `CHANGELOG.md` (move the Unreleased entries to the new version header).
2. Update `README.md` if user-facing behavior changed (commands, config, screens).
3. Update `wiki/` (and its mirror `docs/`) if the release changes architecture, config, or usage.
4. Run the full test suite before committing.

**Tagging (coordinated with the changelog):**
- Tag must point at the release commit and match the CHANGELOG header exactly: `git tag -a vX.Y.Z -m "X.Y.Z — <one-line summary>"`, then `git push` and `git push --tags`.
- Never tag a commit that does not have a CHANGELOG entry for that version.

**Automation:** `python scripts/release.py --bump <patch|minor|major> --note "<summary>"` performs the mechanical steps (bumps `pyproject.toml`, moves `[Unreleased]` → `[X.Y.Z] - date`, prints the exact commit/tag commands) and **refuses to run on a dirty working tree**. `--check` validates repo state (tests pass, changelog format, version/tag consistency) without changing anything. After a pushed major/minor release, run `wiki/sync-wiki.sh` to publish the wiki.

**Commit style**: imperative subject + concise body, mirroring the existing history (`git log --oneline`).

## Docs duplication

- `docs/` and `wiki/` mirror each other (same convention as llm-mailroom, e.g. `docs/architecture.md` == `wiki/Architecture.md`); `wiki/sync-wiki.sh` pushes `wiki/` to the GitHub wiki. Edit both together, or regenerate from one.
- This AGENTS.md is the process/architecture authority; `README.md` is the user-facing entry point; `CHANGELOG.md` is the release record.

## Milestone status (in-flight work)

- **M1 — data core + API + tests**: DONE (mailroom_ui/, server/, tests/ green).
- **M2 — pixel engine + static web**: IN PROGRESS — `web/index.html` + `web/js/sprites.js` exist; `theme.css`, `floor.js`, screen views (`inspector`/`sessions`/`metrics`/`console`), `api.js`, `main.js` are next.
- **M3 — live mode** (WS wiring, envelope animation bound to real trace state, review queue) — planned.
- **M4 — TUI console** (rich, AgentLab-style) — planned.
- **M5 — polish**: `scripts/seed_demo.py`, README/docs, sprite review, acceptance against live traces — planned.
