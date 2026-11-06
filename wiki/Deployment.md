# Deployment Guide — The-Mailroom

The-Mailroom is a **read-only** visualizer. It never writes Langfuse events
and never runs the document graph. Deploy it next to (or pointed at) a live
[`llm-mailroom`](https://github.com/Exios66/llm-mailroom) Langfuse project.

## Prerequisites

- Python 3.11+
- Langfuse project API keys (`LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY`)
- Optional: producer URL + token for REVIEW resolve / Inbox upload
  (`MAILROOM_PIPELINE_URL` / `MAILROOM_PIPELINE_TOKEN`)

Copy `.env.example` → `.env` and fill the Langfuse keys before a local run.

```bash
pip install -e ".[dev]"
python -m server.main          # pixel console on :8001
mailroom-hosted                # Observatory on 0.0.0.0
```

---

## Container topology (constellation)

The-Mailroom only *reads* traces; every other container belongs to the
producer or the local sandbox. Ports as shipped:

| Service | Image / compose file | Port | Talks to |
|---|---|---|---|
| **The-Mailroom** console (`mailroom-web`) | `Dockerfile` (`python -m server.main`) | `:8001` | Langfuse (read), producer `/v1` (operator writes) |
| **The-Mailroom** Observatory (`mailroom-hosted`) | `Dockerfile` default CMD | `:7860` (platform `PORT` wins) | same |
| Operator desk stack | `operator_desk/docker-compose.yml` (`mailroom` from `operator_desk/Dockerfile` with the in-process bin watcher + baked `/desk`, `nginx`) | `:80` only | the visualizer; bins under `/data` |
| llm-mailroom producer | llm-mailroom `deploy/docker-compose.producer.yml` | `:8000` | Langfuse (write), OpenRouter / vLLM / Ollama / llamafile |
| Local LLM sidecars | llm-mailroom `deploy/docker-compose.{ollama,llamafile}.yml` | `:11434` / `:8080` | producer (`DEFAULT_PROVIDER=ollama\|llamafile`) |
| Self-hosted Langfuse 3 (+ postgres, clickhouse, redis, minio) | local-mailroom-sandbox `deploy/docker-compose.yml` | `:3000` | producer + this visualizer |
| Phoenix / vLLM / llama.cpp (sandbox profiles) | same | `:6006` / `:8000` / `:8080` | producer; `MAILROOM_SOURCE=phoenix\|both` here |

Pairing notes:

- Visualizer ↔ producer: `MAILROOM_PIPELINE_URL=http://127.0.0.1:8000`,
  `MAILROOM_PIPELINE_TOKEN` = the producer's `MAILROOM_API_TOKEN`,
  `MAILROOM_PIPELINE_API_PREFIX=/v1`. The sandbox's vLLM also defaults to
  `:8000` — run only one of them on the host port, or remap.
- Visualizer ↔ sandbox Langfuse: `LANGFUSE_HOST=http://localhost:3000` (from
  a container: `http://host.docker.internal:3000`) with the sandbox project's
  keys. US cloud stays the default.
- Anything bound beyond loopback (compose, Spaces, any container host) must set
  `MAILROOM_OPERATOR_JWT_SECRET` and a non-default
  `MAILROOM_OPERATOR_ADMIN_PASSWORD`: operator login, review resolve and
  inbox upload fail closed otherwise (read-only display keeps working).

## Hosted Observatory (Hugging Face Docker Space)

The hosted target is the **Hugging Face Docker Space pair**: this
Observatory plus the llm-mailroom producer Space for REVIEW resolve. Railway
was retired on 2026-11-06 (ADR-005); the repo no longer ships Railway config.

The root `Dockerfile` is the Space image (`MAILROOM_EDITION=hosted`,
`0.0.0.0:7860`, `python -m server.hosted`). Publish with
`scripts/publish_space.py`; Langfuse keys stay Space **secrets**, never the git
tree. Details: [`hosted/SPACE_README.md`](../hosted/SPACE_README.md).

```bash
python scripts/publish_space.py --check                         # validate the payload
python scripts/publish_space.py --repo <user>/mailroom-observatory  # HF_TOKEN + LANGFUSE_* in env
```

Deploys probe `GET /health` (fast process liveness, **not** a Langfuse call).
`GET /api/health` remains the SPA / TUI source-reachability check. Both
`/health` and `/api/meta` carry `platform` (`huggingface` / `render` / `fly`)
and `build_sha` (baked from the `MAILROOM_BUILD_SHA` build arg), so a deploy can
be checked at a glance.

### Space secrets and variables

| Variable | Value |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | Langfuse project public key (secret) |
| `LANGFUSE_SECRET_KEY` | Langfuse project secret key (secret) |
| `LANGFUSE_HOST` | `https://us.cloud.langfuse.com` (or EU / self-hosted) |
| `MAILROOM_PIPELINE_URL` | producer Space URL (optional REVIEW pairing) |
| `MAILROOM_PIPELINE_TOKEN` | same secret as producer `MAILROOM_API_TOKEN` |
| `MAILROOM_PIPELINE_API_PREFIX` | `/v1` |

Optional Hub/eval knobs (same as the producer side):

| Variable | Value |
|---|---|
| `MAILROOM_TRACE_LIMIT` | `100` (keeps floor polls snappy) |
| `HF_TOKEN` | Hub token (eval / sync / Space publish) |
| `MAILROOM_HF_DATASET` | `Lucius-Morningstar/mailroom-dataset` |
| `MAILROOM_HF_REVISION` | corrected GT tip (see `mailroom_ui/hf_corpus.py`) |
| `MAILROOM_HF_CONFIG` | `ground_truth` |

Display stays Langfuse-only. Without Langfuse keys the UI shows
**MAILROOM CLOSED**, never canned envelopes; the process still passes
`GET /health`.

Verify the pair after a publish:

```bash
curl -sS https://<space>.hf.space/health      # liveness (+ platform, build_sha)
curl -sS https://<space>.hf.space/api/health  # Langfuse / cache status
# from an llm-mailroom checkout:
PYTHONPATH=src python src/scripts/probe_hosted_spaces.py
```

## Other container hosts

The same image runs on any host that injects secrets. The server prefers the
platform **`PORT`** over `MAILROOM_PORT` (image default `7860`), so the process
binds where the host's edge expects. Pass the commit at build time with
`--build-arg MAILROOM_BUILD_SHA=$(git rev-parse HEAD)`.

If a host shows a crash or restart loop:

- Check the logs show `Uvicorn running on http://0.0.0.0:<PORT>` with the
  host's `PORT`, not a hard-coded 7860.
- Check `curl /health` answers quickly with `"status":"alive"` even when
  `/api/health` reports `"ok": false` (MAILROOM CLOSED).

---

## GitHub Pages (static snapshot)

Deploy-from-branch only — `scripts/publish_pages.sh` → `gh-pages:/docs`.
No Actions. See [`.cursor/skills/gh-pages/SKILL.md`](../.cursor/skills/gh-pages/SKILL.md).
