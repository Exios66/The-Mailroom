# The-Mailroom

**Pixel-art visual engine for the `llm-mailroom` multi-agent legal-document
pipeline.** The Mailroom renders every pipeline run as an animated conveyor of
document envelopes — sorter, specialist bays, the boss's desk, the reporter,
the archive — driven entirely by **Langfuse traces**. Langfuse is the sole
source of truth: every envelope, badge, verdict, and metric on screen is
derived from the pipeline's Langfuse project. Nothing is fabricated, nothing
falls back to local data.

```
pip install -e ".[dev]"
cp .env.example .env      # add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-web              # → http://127.0.0.1:8001
```

## What you see

- **FLOOR** — the mailroom: a conveyor belt carrying document envelopes
  through three rooms (Intake & Sort · Extraction & Adjudication · Reporting
  & Archive), with a blinking human-review siding and a failed bin. Click an
  envelope for its full run.
- **REVIEW** — the review siding as a queue: every run waiting on a human,
  with its escalation reason and confidence, one click from its inspector.
- **INSPECTOR** — drill-down into any trace: node-span timeline, LLM
  generations (model, tokens, latency, cost), confidence and judge scores.
- **SESSIONS** — matter explorer grouped by Langfuse session.
- **METRICS** — docs processed, archived/review/failed, cost, tokens, p95
  generation latency, judge-verdict mix, per-doc-type counts.
- **CONSOLE** — a live scrolling log of the pipeline, AgentLaboratory-style.

## Demo data (play-testing without a live run)

Demo runs are seeded **into** Langfuse (env `demo`) — the visualizer still
reads Langfuse only, so nothing on screen is ever canned data:

```bash
python scripts/seed_demo.py                       # seed 10 demo runs
python scripts/seed_demo.py --list-scenarios      # what the demo set covers
python scripts/seed_demo.py --check --check-api   # verify seeded runs against
                                                  # stored Langfuse logs AND the
                                                  # running server's display API
python scripts/seed_demo.py --check-logs <dir>    # verify against run logs saved
                                                  # by llm-mailroom's
                                                  # scripts/sync_langfuse_logs.py
```

## Requirements

- Python 3.11+
- A Langfuse project (the `llm-mailroom` project on US cloud by default)
  with project-scoped API keys in `.env`
- The sister pipeline repo `../llm-mailroom` (optional — only needed to use
  the `MAILROOM_TAXONOMY` live-config override; see `AGENTS.md`)

## Configuration

All knobs live in `.env` (see `.env.example`): Langfuse keys/host
(`LANGFUSE_HOST`, default `https://us.cloud.langfuse.com`), poll cadence
(`MAILROOM_POLL_INTERVAL`), recent window, trace limit, optional tag/env
filters, `MAILROOM_PORT` (default `8001`), and `MAILROOM_TAXONOMY`.

## Project layout

```
mailroom_ui/   data core — Langfuse adapter, trace interpreter, topology
               mirror, models, metrics (reads Langfuse only)
server/        FastAPI, read-only: /api/* + WebSocket + serves web/
web/           pixel-art SPA (vanilla HTML/CSS/JS, no build step)
tui/           rich console (planned)
scripts/       seed_demo (demo runs INTO Langfuse + verification) · release
docs/ + wiki/  mirrored documentation (wiki/sync-wiki.sh publishes the wiki)
tests/         pytest suite against a fake Langfuse client — never the real API
```

## Tests

```bash
python -m pytest tests/ -q
```

## Releases

Semantic versioning with a Keep-a-Changelog `CHANGELOG.md`, README/wiki
updates on major changes, and annotated `vX.Y.Z` tags matching the changelog.
`python scripts/release.py --help` drives the mechanical steps. See
`AGENTS.md` → "Release process" for the full procedure.

## License & credits

Visual palette and character direction derived from the AgentLaboratory
project's artwork. Built for the `llm-mailroom` pipeline; see that repo for
the pipeline itself.
