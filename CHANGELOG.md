# Changelog

All notable changes to The-Mailroom are documented here, following
[Keep a Changelog](https://keepachangelog.com) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Langfuse v4 SDK tolerance: camelCase observation fields (`startTime`,
  `endTime`, `modelId`, `totalTokens`, `inputTokens`, `outputTokens`,
  `totalCost`, trace `sessionId`/`updatedAt`/`createdAt`) accepted alongside
  v2/v3 snake_case shapes (`trace_interpreter.py` `_both`/`_pick` helpers).
- `tests/fake_langfuse.py:make_trace_v4` — v4-shaped (camelCase) trace
  fixture; interpreter tests cover both shapes.
- M2 (in progress): `web/index.html` app shell and `web/js/sprites.js`
  hand-authored pixel-art palette + sprites (agents, envelopes, stamps, bins,
  conveyor, terminals) derived from the AgentLaboratory visual analysis.

### Changed
- Generation cost is read from `cost_details` (v2/v3) or top-level
  `totalCost`/`totalPrice` (v4), never from a single fixed field.

### Fixed
- Cost extraction regressed during v4 tolerance work — observations were
  searched for cost at the wrong level, zeroing all run costs.

## [0.1.0] - 2026-08-10

### Added
- M1 data core: `mailroom_ui` package — `langfuse_source.py` (Langfuse SDK
  adapter + `TTLCache`), `trace_interpreter.py` (trace → `PipelineRun`),
  `pipeline_schema.py` (topology mirror, `MAILROOM_TAXONOMY` override),
  `models.py` (pydantic), `metrics.py` (aggregations).
- M1 server: FastAPI read-only API (`/api/health`, `/api/traces`,
  `/api/traces/{id}`, `/api/metrics`, `/api/sessions[/{id}]`,
  `/api/review-queue`, `/api/meta`, WebSocket `/ws`) with background
  `PollHub` snapshot broadcaster (`server/poller.py`).
- M1 tests: fake Langfuse client (`tests/fake_langfuse.py`) — the suite never
  touches the real API.
- Re-run clustering: deterministic trace ids are reused by pilot/attempt
  re-runs, so observations are clustered by time gap (`RUN_GAP_S`) and only
  the latest run's spans/generations are displayed.
- Retry detection via explicit retry stages (`RETRY_CLASSIFY` /
  `RETRY_EXTRACT`) instead of duplicate-based heuristics.
- Trace listing filter by trace `name` (`document-pipeline`) to keep the
  floor/poller focused on pipeline runs.
- Project scaffolding: `pyproject.toml`, `.env.example`, `.gitignore`,
  `mailroom-web` console entrypoint.
