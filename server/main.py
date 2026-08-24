"""The-Mailroom web server: Langfuse-backed read-only API + pixel-art UI."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# V-8: .env must be loaded BEFORE any module-level env reads (the knobs below
# were read before load_dotenv(), so MAILROOM_POLL_INTERVAL / RECENT_WINDOW /
# TRACE_LIMIT never applied from .env).
load_dotenv()

from mailroom_ui.langfuse_source import (
    LangfuseSource,
    LangfuseUnavailable,
    enriched_recent_runs,
    list_recent_runs,
)
from mailroom_ui.metrics import compute_metrics
from mailroom_ui.models import PipelineRun, SessionSummary
from mailroom_ui.pipeline_schema import DOC_CLASSES
from mailroom_ui.trace_interpreter import interpret_trace
from server.poller import PollHub, floor_payload

log = logging.getLogger("mailroom.server")

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
RECENT_WINDOW = float(os.environ.get("MAILROOM_RECENT_WINDOW", 6 * 3600))
POLL_INTERVAL = float(os.environ.get("MAILROOM_POLL_INTERVAL", "3"))
TRACE_LIMIT = int(os.environ.get("MAILROOM_TRACE_LIMIT", "100"))


def create_app(source: Optional[LangfuseSource] = None) -> FastAPI:
    src = source or LangfuseSource()
    hub = PollHub(src, interval=POLL_INTERVAL, window=RECENT_WINDOW, limit=TRACE_LIMIT)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await hub.start()
        yield
        await hub.stop()

    app = FastAPI(title="The-Mailroom", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(LangfuseUnavailable)
    async def langfuse_down_handler(request, exc):
        return JSONResponse(
            status_code=503,
            content={"error": "langfuse unavailable", "detail": str(exc)},
        )

    # V-18: any other server error must come back as JSON with a detail the
    # SPA can show — the old default 500 was plain text and the frontend
    # discarded it, leaving a silent blank/zeroed screen.
    @app.exception_handler(Exception)
    async def generic_error_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"error": "internal server error", "detail": str(exc)[:300]},
        )

    @app.get("/api/health")
    def health():
        return src.health()

    @app.get("/api/traces")
    def traces(
        since: int = Query(1800, ge=0, le=86400 * 7, description="window seconds"),
        limit: int = Query(TRACE_LIMIT, ge=1, le=500),
        stage: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        runs = _recent(src, since, limit)
        if stage:
            runs = [r for r in runs if r.stage.value == stage]
        if environment:
            runs = [r for r in runs if r.environment == environment]
        return {
            "count": len(runs),
            "source": "langfuse",
            "runs": [_serialize(r) for r in runs],
        }

    @app.get("/api/traces/{trace_id}")
    def trace_detail(trace_id: str):
        run = src.get_run(trace_id)
        if run is None:
            # FastAPI has no Flask-style (body, status) tuple returns — the
            # tuple was serialized as a 200 JSON array.
            return JSONResponse(status_code=404, content={"error": "trace not found"})
        return _serialize(run, full=True)

    @app.get("/api/metrics")
    def metrics(since: int = Query(3600, ge=0, le=86400 * 7)):
        # V-3: aggregate ENRICHED runs (full observations/scores), never light
        # ones — light runs have no generations, so cost/tokens/calls were
        # permanently $0.00 / 0 tok / 0 calls. get_run() is cached, so this
        # shares fetches with the poller instead of adding another N+1.
        runs = enriched_recent_runs(src, since=_utcnow() - timedelta(seconds=since), limit=TRACE_LIMIT)
        m = compute_metrics(runs, since=_utcnow() - timedelta(seconds=since))
        return {"source": "langfuse", **m.model_dump()}

    @app.get("/api/sessions")
    def sessions(limit: int = Query(50, ge=1, le=200)):
        raw = src.list_sessions(limit=limit)
        out = []
        for s in raw:
            # V-19: sessions are displayed as runs, and runs need their
            # observations/scores — interpret_trace() without scores produced
            # light runs with no verdicts/tokens/cost on every card.
            # get_run() is cached; the per-session trace fetch is capped so a
            # session with hundreds of traces can't stall the summary.
            runs = _session_runs(src, s.get("id", ""), limit=20)
            out.append(
                SessionSummary(
                    id=s.get("id", ""),
                    name=s.get("name"),
                    created_at=_dt(s.get("created_at")),
                    updated_at=_dt(s.get("updated_at")),
                    trace_count=len(runs),
                    runs=runs,
                )
            )
        out.sort(key=lambda s: s.updated_at or datetime.min, reverse=True)
        return {"count": len(out), "source": "langfuse", "sessions": [s.model_dump() for s in out]}

    @app.get("/api/sessions/{session_id}")
    def session_detail(session_id: str):
        runs = _session_runs(src, session_id, limit=200)
        return {
            "session_id": session_id,
            "count": len(runs),
            "source": "langfuse",
            "runs": [_serialize(r) for r in runs],
        }

    @app.get("/api/review-queue")
    def review_queue(since: int = Query(86400 * 7, ge=0, le=86400 * 7)):
        # V-20: enriched runs (verdicts/tokens/cost on the cards, not zeros);
        # the queue can legitimately exceed the floor's 100-run limit, so use
        # the wider 500 cap.
        runs = [r for r in enriched_recent_runs(src, since=_utcnow() - timedelta(seconds=since), limit=500)
                if r.needs_human]
        return {"count": len(runs), "source": "langfuse", "runs": [_serialize(r) for r in runs]}

    @app.get("/api/meta")
    def meta():
        # V-23: use PipelineSchema.load() so the MAILROOM_TAXONOMY override is
        # reflected — the module-level DOC_CLASSES constant ignored it.
        try:
            from mailroom_ui.pipeline_schema import PipelineSchema

            schema = PipelineSchema.load()
            classes = schema.doc_classes if hasattr(schema, "doc_classes") else DOC_CLASSES
        except Exception:
            classes = DOC_CLASSES
        return {"doc_classes": classes, "source": "langfuse"}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await hub.connect(ws)
        try:
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            hub.disconnect(ws)
        except Exception:
            hub.disconnect(ws)

    if WEB_DIR.exists():
        app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

        @app.get("/")
        def index():
            # V-22: no-cache on index.html so a deployed SPA is never stale.
            return FileResponse(
                WEB_DIR / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
            )

    return app


def _utcnow() -> datetime:
    """Langfuse stores UTC — every query window must be UTC-aware (a naive
    local now() shifts the window by the machine's UTC offset)."""
    return datetime.now(timezone.utc)


def _recent(src: LangfuseSource, since: int, limit: int) -> list[PipelineRun]:
    since_dt = _utcnow() - timedelta(seconds=since)
    return list_recent_runs(src, since=since_dt, limit=limit)


def _session_runs(src: LangfuseSource, session_id: str, limit: int) -> list[PipelineRun]:
    """Enriched runs for one session, newest first (V-19).

    Uses the cached get_run() (observations+scores) with per-trace isolation:
    one bad trace falls back to its light interpretation instead of failing
    the whole session.
    """
    runs: list[PipelineRun] = []
    try:
        traces = src.get_session_traces(session_id, limit=limit)
    except Exception as exc:
        log.warning("session traces failed for %s: %s", session_id, exc)
        return runs
    for t in traces:
        tid = t.get("id")
        if not tid:
            continue
        try:
            full = src.get_run(tid)
            runs.append(full if full is not None else interpret_trace(t))
        except Exception as exc:
            log.warning("session run failed for %s: %s", tid, exc)
            runs.append(interpret_trace(t))
    runs.sort(key=lambda r: r.updated_at or datetime.min, reverse=True)
    return runs


def _serialize(run: PipelineRun, full: bool = False) -> dict:
    if not full:
        return floor_payload(run)
    return {
        **floor_payload(run),
        "spans": [s.model_dump() for s in run.spans],
        "generations": [g.model_dump() for g in run.generations],
        "scores": run.scores,
    }


def _dt(value) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    load_dotenv()
    port = int(os.environ.get("MAILROOM_PORT", "8001"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    run()
