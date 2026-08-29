---
title: Mailroom Observatory
emoji: 📬
colorFrom: pink
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Live accessible desk for the llm-mailroom pipeline
---

# Mailroom Observatory

Hosted edition of [The-Mailroom](https://github.com/Exios66/The-Mailroom):
a public, accessible operations desk for the `llm-mailroom` legal-document
pipeline. It reads **Langfuse only** (keys are Space **secrets**, never the
browser and never this README).

This Space is **not** the GitHub Pages snapshot and **not** the local
pixel-art console. `/` is the Observatory (`MAILROOM_EDITION=hosted`).
The pixel console assets stay under `/static`. Same `/api/*` + `/ws`
contract as `mailroom-hosted`.

## Hugging Face dashboard

| Setting | Value |
|---|---|
| SDK | **Docker** (not Gradio / Streamlit / static) |
| Root directory | Space repo root (the committed `Dockerfile`) |
| App port | **7860** |
| Hardware | CPU basic is enough (no GPU — this process does not serve models) |
| Visibility | Public UI; keep Langfuse keys as **Secrets** |

### Secrets (Settings → Variables and secrets → Secrets)

| Name | Notes |
|---|---|
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-…` from Langfuse → Settings → API Keys |
| `LANGFUSE_SECRET_KEY` | `sk-lf-…` (never a regular variable) |
| `LANGFUSE_HOST` | Production US cloud: `https://us.cloud.langfuse.com` |

This visualizer reads **`LANGFUSE_HOST`**. If you only have Langfuse's
`LANGFUSE_BASE_URL`, set that instead — the server accepts it as an alias.

### Variables (optional, not secret)

| Name | Default |
|---|---|
| `MAILROOM_SOURCE` | `langfuse` |
| `MAILROOM_EDITION` | `hosted` (already set in the Dockerfile) |
| `MAILROOM_TRACE_ENVIRONMENTS` | unset = show every env on the floor |
| `MAILROOM_TRACE_TAGS` | unset = no tag filter |
| `MAILROOM_TRACE_CACHE_DIR` | `/tmp/mailroom-trace-cache` (ephemeral; lost on sleep) |
| `MAILROOM_POLL_ENRICH` | `inflight` (do not set `all` on the Space) |

Do **not** put `HF_TOKEN` or Langfuse keys in Variables (they are visible
to Space collaborators as plain text). The Hub token is only needed on
your laptop to run `scripts/publish_space.py`.

Human-review **resolve** and the Inbox **Queue a document** form still need
a reachable llm-mailroom producer (`MAILROOM_PIPELINE_URL` +
`MAILROOM_PIPELINE_TOKEN` as **Secrets**). Without them the desk stays
read-only: REVIEW and enqueue return an honest 503. The floor uses a
Langfuse-derived JSON cache so inspect does not wait 30s on `get_run`;
**Export snapshot** downloads that bundle. Empty cache + Langfuse down
is MAILROOM CLOSED.

## Republish

From the GitHub checkout (keys stay in the environment):

```bash
pip install huggingface_hub
HF_TOKEN=hf_... \
  LANGFUSE_PUBLIC_KEY=pk-lf-... \
  LANGFUSE_SECRET_KEY=sk-lf-... \
  LANGFUSE_HOST=https://us.cloud.langfuse.com \
  python scripts/publish_space.py --repo <user>/mailroom-observatory
```

`--check` validates the Docker payload without calling the Hub.
