"""The-Mailroom web server: Langfuse-backed read-only API + pixel-art UI."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from mailroom_ui.langfuse_source import LangfuseSource, list_recent_runs
from mailroom_ui.metrics import compute_metrics
from mailroom_ui.models import PipelineRun, SessionSummary
from mailroom_ui.pipeline_schema import DOC_CLASSES
from mailroom_ui.trace_interpreter import interpret_trace
from server.poller import PollHub

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

    @app.get("/api/health")
    def health():
        return {"status": "ok", "source": "langfuse", "langfuse": src.available}

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
            return {"error": "trace not found"}, 404
        return _serialize(run, full=True)

    @app.get("/api/metrics")
    def metrics(since: int = Query(3600, ge=0, le=86400 * 7)):
        runs = _recent(src, since, TRACE_LIMIT)
        m = compute_metrics(runs, since=datetime.now() - timedelta(seconds=since))
        return {"source": "langfuse", **m.model_dump()}

    @app.get("/api/sessions")
    def sessions(limit: int = Query(50, ge=1, le=200)):
        raw = src.list_sessions(limit=limit)
        out = []
        for s in raw:
            traces = src.get_session_traces(s.get("id", ""), limit=50)
            runs = [interpret_trace(t) for t in traces]
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
        traces = src.get_session_traces(session_id, limit=200)
        runs = [interpret_trace(t) for t in traces]
        return {
            "session_id": session_id,
            "count": len(runs),
            "source": "langfuse",
            "runs": [_serialize(r) for r in runs],
        }

    @app.get("/api/review-queue")
    def review_queue(since: int = Query(86400 * 7, ge=0, le=86400 * 7)):
        runs = [r for r in _recent(src, since, TRACE_LIMIT) if r.needs_human]
        return {"count": len(runs), "source": "langfuse", "runs": [_serialize(r) for r in runs]}

    @app.get("/api/meta")
    def meta():
        return {"doc_classes": DOC_CLASSES, "source": "langfuse"}

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
            return FileResponse(WEB_DIR / "index.html")

    return app


def _recent(src: LangfuseSource, since: int, limit: int) -> list[PipelineRun]:
    since_dt = datetime.now() - timedelta(seconds=since)
    return list_recent_runs(src, since=since_dt, limit=limit)


def _serialize(run: PipelineRun, full: bool = False) -> dict:
    if not full:
        from server.poller import floor_payload

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
    port = int(os.environ.get("MAILROOM_PORT", "8001"))
    uvicorn.run(create_app(), host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    run()
