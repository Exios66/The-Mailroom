# The-Mailroom

![version](https://img.shields.io/badge/version-0.2.0-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![data source](https://img.shields.io/badge/data%20source-Langfuse%20only-6C5CE7)

**Pixel-art visual engine for the [`llm-mailroom`](https://github.com/Exios66/llm-mailroom)
multi-agent legal-document pipeline.** The Mailroom renders every pipeline run as an
animated conveyor of document envelopes — sorter, specialist bays, the boss's desk,
the reporter, the archive — driven entirely by **Langfuse traces**. Langfuse is the
sole source of truth: every envelope, badge, verdict, and metric on screen is derived
from the pipeline's Langfuse project. Nothing is fabricated, nothing falls back to
local data.

---

## The governed constellation

The-Mailroom is one node of a governed family of repositories sharing one kanban
board, one discussion log, and one trace contract:

```
        ┌─────────────────────────┐         ┌─────────────────────────┐
        │  llm-entity-extraction  │ breeds  │      llm-mailroom       │
        │  prompt-experiment loop │ ──────▶ │   the document pipeline  │
        └─────────────────────────┘         └────────────┬────────────┘
                                                         │ Langfuse traces (US cloud)
                                                         ▼
                                        ┌──────────────────────────────┐
                             YOU ARE    │         THE-MAILROOM         │
                               HERE ▶   │    pixel-art visual engine   │
                                        └──────────────────────────────┘
```

| Repository | Role | Relationship to The-Mailroom |
|---|---|---|
| [llm-mailroom](https://github.com/Exios66/llm-mailroom) | LangGraph state machine processing legal documents through specialist LLM agents (classify → extract → report → archive) | **Upstream** — its Langfuse project is this visualizer's sole data source |
| [llm-entity-extraction](https://github.com/Exios66/llm-entity-extraction) | Prompt-experiment loop (prompt versions × models, paired-bootstrap ablations) | Breeds the pipeline's sorter/specialist prompts; hosts the shared kanban board + governance log for the whole chain |
| [llm-dojo-scoring](https://github.com/Exios66/llm-dojo-scoring) | Deterministic, field-type-aware scoring engine (`@v0.7.0`) | Upstream governed dependency of both pipeline repos |
| [Enron-Evaluation-Environment](https://github.com/Exios66/Enron-Evaluation-Environment) | EDA + pipeline-ready correspondence dataset (CMU Enron corpus) | Corpus feed for the pipeline's `correspondence` doc class |
| [claims-data-eda](https://github.com/Exios66/claims-data-eda) | Insurance-claims candidate-corpus EDA (CMS DE-SynPUF direction) | Candidate corpus feed for the `insurance_claim` doc class |
| [atticus-investigation](https://github.com/Exios66/atticus-investigation) | LegalBench classification prompt-engineering pipeline | Eval sibling — same methodology family, LegalBench focus |
| [llm-mailroom-graph](https://exios66.github.io/llm-mailroom-graph/) · [llm-entity-extraction-graph](https://exios66.github.io/llm-entity-extraction-graph/) | Interactive graphify knowledge graphs | Derived sites mapping the pipeline's and the loop's code structure |

Full relationship map: [`llm-mailroom/docs/sister-repos.md`](https://github.com/Exios66/llm-mailroom/blob/main/docs/sister-repos.md).

---

## Quick start

```bash
pip install -e ".[dev]"
cp .env.example .env      # add LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
mailroom-web              # → http://127.0.0.1:8001
mailroom-tui              # AgentLab-style live console (same data, in a terminal)
```

## What you see

- **FLOOR** — the mailroom: a conveyor belt carrying document envelopes
  through the pipeline's seven stations (SORTER · EXTRACT · JUDGE · BOSS ·
  REPORT · ARCHIVE, plus the human-review siding) grouped into three rooms
  (Intake & Sort · Extraction & Adjudication · Reporting & Archive). The
  JUDGE station is the KANBAN-063 quality gate (`judge_verify` +
  `arbitrate-verdict`). Click an envelope for its full run.
- **REVIEW** — the review siding as a queue: every run waiting on a human,
  with its escalation reason and confidence, one click from its inspector.
- **INSPECTOR** — drill-down into any trace: node-span timeline, LLM
  generations (model, tokens, latency, cost), confidence and judge scores.
- **SESSIONS** — matter explorer grouped by Langfuse session.
- **METRICS** — docs processed, archived/review/failed, cost, tokens, p95
  generation latency, judge-verdict mix, per-doc-type counts.
- **CONSOLE** — a live scrolling log of the pipeline, AgentLaboratory-style.
- **TUI** (`mailroom-tui`) — the same pipeline in a terminal: per-doc tables,
  `*** Beginning station: ... ***` banners as runs arrive and advance, judge
  verdict banners, review siding, metrics, and full trace inspection. It
  subscribes to the same WebSocket floor snapshots as the web UI (`--once`
  renders a single frame for scripting).

---

## Demo data (play-testing without a live run)

Demo runs are seeded **into** Langfuse (env `demo`) — the visualizer still
reads Langfuse only, so nothing on screen is ever canned data:

```bash
python scripts/seed_demo.py                       # seed 13 demo runs (incl.
                                                  # judge-gate + arbiter paths)
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

> [!IMPORTANT]
> `pipeline_schema.py` is cached at process level — editing `taxonomy.yaml`
> (or pointing `MAILROOM_TAXONOMY` at the pipeline's copy) requires a server
> restart to take effect.

---

## The trace contract & the mirror duty

The-Mailroom does not own the trace contract it renders — it **mirrors** it
from the upstream pipeline. This is the repo's #1 maintenance duty: when
`llm-mailroom` changes span names, node order, the agent roster (15 agents),
doc classes (7 classes), confidence thresholds, or judge score names
(`mailroom-pipeline-judge`, `mailroom-pipeline-quality`), this repo must
update `mailroom_ui/pipeline_schema.py` and `mailroom_ui/trace_interpreter.py`
in the same change window.

Until mirrored, breakage is visible by design: new spans render as an
`unknown` stage, new doc classes fall back to the gray default stamp color,
renamed judge scores vanish from runs. The full contract — span inventory,
score names, metadata/tags, and the complete breakage map — lives in
[`AGENTS.md`](AGENTS.md) ("Sister repo" section), which is authoritative for
pipeline internals alongside the pipeline's own `AGENTS.md`.

---

## Project layout

```
mailroom_ui/   data core — Langfuse adapter, trace interpreter, topology
               mirror, models, metrics (reads Langfuse only)
server/        FastAPI, read-only: /api/* + WebSocket + serves web/
web/           pixel-art SPA (vanilla HTML/CSS/JS, no build step)
tui/           rich console — the pipeline in a terminal (mailroom-tui)
scripts/       seed_demo (demo runs INTO Langfuse + verification) · release
docs/ + wiki/  mirrored documentation (wiki/sync-wiki.sh publishes the wiki)
tests/         pytest suite against a fake Langfuse client — never the real API
```

## Tests

```bash
python -m pytest tests/ -q
```

Tests never hit real Langfuse — `tests/fake_langfuse.py` provides v2/v3
snake_case and v4 camelCase fixtures mirroring the trace contract.

## Releases

Semantic versioning with a Keep-a-Changelog `CHANGELOG.md`, README/wiki
updates on major changes, and annotated `vX.Y.Z` tags matching the changelog.
`python scripts/release.py --help` drives the mechanical steps. See
`AGENTS.md` → "Release process" for the full procedure.

---

## License & credits

Visual palette and character direction derived from the AgentLaboratory
project's artwork. Built for the `llm-mailroom` pipeline — see that repo and
its [sister-repos map](https://github.com/Exios66/llm-mailroom/blob/main/docs/sister-repos.md)
for the full governed constellation. No license published yet.
