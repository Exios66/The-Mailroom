---
name: mailroom-tool-router
description: Choose the correct The-Mailroom stack for tracing, UI surfaces, schema sync, Pages, TUI, Hugging Face evals, and sister-repo serving. Use at the start of any Langfuse, Phoenix, Braintrust, Ollama, Modal, pixel floor, Observatory, poller, or taxonomy task so only the most appropriate skill is used.
---

# Mailroom tool router

Read this skill **first** when the task touches traces, sources, the conveyor,
Observatory, TUI, Pages, the operator desk, or sister repos. Then open exactly one specialty skill
below. Do not invent a second document-display backend or a Node/LLM client in
this visualizer.

## Decision table

| Job | Use | Skill | Do **not** use |
| --- | --- | --- | --- |
| Default document display | Configured source adapters; Langfuse is the default | [langfuse](../langfuse/SKILL.md) for Langfuse; [apache-phoenix](../apache-phoenix/SKILL.md) for Phoenix | Forcing a primary sink when another conformant adapter is configured; canned JSON on the live path |
| Optional local OTEL source | `MAILROOM_SOURCE=phoenix` or `both` | [apache-phoenix](../apache-phoenix/SKILL.md) | Phoenix as a replacement for the US-cloud `llm-mailroom` project |
| Hosted eval / experiment logs | not this repo | [braintrust](../braintrust/SKILL.md) | A `MAILROOM_SOURCE=braintrust` adapter |
| Hub GT / production-pilot scripts | `scripts/eval_pipeline.py`, `run_production_pilot.py` | [huggingface](../huggingface/SKILL.md) | Live Qwen/Hub unless explicitly asked; Dojo imports in the live display path (offline `[eval]` uses Dojo) |
| Local LLM inference | `local-mailroom-sandbox` / `llm-mailroom` | [ollama](../ollama/SKILL.md) | An Ollama client inside The-Mailroom |
| Remote GPU vLLM | sandbox `modal-vllm` | [modal](../modal/SKILL.md) | Modal deploy from this repo |
| Pixel conveyor / SPA | `web/` vanilla HTML/CSS/JS | [pixel-console](../pixel-console/SKILL.md) | npm / webpack / React |
| Public hosted desk | `hosted/` + `mailroom-hosted` | [observatory](../observatory/SKILL.md) | Treating GH Pages as the Observatory |
| Hugging Face Space (live Observatory) | `scripts/publish_space.py` + root `Dockerfile` | [observatory](../observatory/SKILL.md) | Gradio/FastAPI/Vercel Space SDK; baking Langfuse keys into git |
| Live poll, WS, watcher lamp | `server/poller.py`, `/api/pipeline` | [live-floor](../live-floor/SKILL.md) | Fabricated envelopes while Langfuse is down |
| Human review resolve | Pixel/Observatory REVIEW + `mailroom-tui --resolve` | [pixel-console](../pixel-console/SKILL.md) / [observatory](../observatory/SKILL.md) / [tui](../tui/SKILL.md) | Pointing `MAILROOM_API_URL` at producer `:8000`; resolving from snapshot mode |
| Span/stage/taxonomy drift | `mailroom_ui/pipeline_schema.py` | [pipeline-schema-sync](../pipeline-schema-sync/SKILL.md) | Editing schema without interpreter + tests + CHANGELOG |
| Static snapshot site | `scripts/publish_pages.sh` | [gh-pages](../gh-pages/SKILL.md) | GitHub Actions for Pages |
| Terminal console | `mailroom-tui` | [tui](../tui/SKILL.md) | Pointing `MAILROOM_API_URL` at producer `:8000` |
| Operator desk (auth / archive / ops / bin observer) | `operator_desk/` on `:8001` (`/v1/*`, `/ws/pipeline`) | [operator-desk](../operator-desk/SKILL.md) | Treating operator SQLite as a display source |
| Optional React operator desk | `ui/` (`the-mailroom-ui`, `/desk` when built) | [optional-ui](../optional-ui/SKILL.md) | Replacing `web/` or `hosted/` with npm; making Node required for `mailroom-web` |

## Source precedence (`MAILROOM_SOURCE`)

Canonical default in `.env.example`: **`MAILROOM_SOURCE=langfuse`**.
Select `phoenix` or another registered adapter when that is the configured sink.

1. **langfuse** — primary document-trace adapter (the default).
2. **phoenix** — primary Arize Phoenix adapter via `PHOENIX_ENDPOINT`.
3. **langfuse,phoenix** (alias **both**) — `MultiSource` union; still no fabricated rows.
   Any comma list of registered adapters works (`mailroom_ui/source_registry.py`);
   a new backend must pass `tests/source_conformance.py`.
4. Any other conformant adapter registers through `mailroom.sources`; the UI must not require either primary backend.
5. All configured sources unreachable → **MAILROOM CLOSED**, not stale/canned data.

Operator liveness (watcher heartbeat, inbox pending) and **human-review
resolve** (`POST /api/review/resolve` → approve / reject / record / requeue /
complete; optional `doc_type` mapped to producer `override_doc_type`;
`GET /api/review/source` for parked text, with catalog lookup fallback)
may go through `MAILROOM_PIPELINE_URL` on the visualizer server. That is
**not** document display data; the browser never holds the producer token.

## Serving note (this repo does not serve models)

Ollama / Modal / OpenRouter / vLLM belong in
[`local-mailroom-sandbox`](https://github.com/Exios66/local-mailroom-sandbox)
or [`llm-mailroom`](https://github.com/Exios66/llm-mailroom). This process is
read-only FastAPI on `:8001`.

## Repo anchors

| Concern | Path |
| --- | --- |
| Env template | `.env.example` |
| Langfuse adapter | `mailroom_ui/langfuse_source.py` |
| Phoenix adapter | `mailroom_ui/phoenix_source.py` |
| Topology mirror | `mailroom_ui/pipeline_schema.py` |
| Poller / WS | `server/poller.py`, `/ws` |
| Pixel SPA | `web/` |
| Observatory | `hosted/` |
| TUI | `tui/mailroom_console.py` |
| Operator desk | `operator_desk/` |
| Process authority | `AGENTS.md` |
| Project skills (this tree) | `.cursor/skills/*/SKILL.md` |

## Quick commands

```bash
pip install -e ".[dev]"
pip install -e ".[pipeline]"  # optional llm-mailroom pin @ 9e8f30b279e7626c056b03511f823105760f80d7 (0.9.1, reviewed source adoption)
cp .env.example .env          # LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY
python -m pytest tests/ -q    # never hits real Langfuse
python -m server.main         # pixel :8001 + Observatory /live
mailroom-hosted               # Observatory on 0.0.0.0
mailroom-tui
python scripts/publish_space.py --check
```
