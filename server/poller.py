"""Background poller: Langfuse -> compact run snapshots -> WebSocket clients."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import WebSocket

from mailroom_ui.langfuse_source import LangfuseSource, list_recent_runs
from mailroom_ui.models import PipelineRun

log = logging.getLogger("mailroom.poller")


def floor_payload(run: PipelineRun) -> dict[str, Any]:
    """Compact serialization for the floor view (list-level data only)."""
    return {
        "trace_id": run.trace_id,
        "filename": run.filename,
        "matter_id": run.matter_id,
        "session_id": run.session_id,
        "environment": run.environment,
        "tags": run.tags,
        "attempt": run.attempt,
        "stage": run.stage.value,
        "phase": run.phase.value,
        "doc_type": run.doc_type,
        "classification_confidence": run.classification_confidence,
        "extraction_confidence": run.extraction_confidence,
        "review_decision": run.review_decision,
        "escalation_reason": run.escalation_reason,
        "error_message": run.error_message,
        "verdict": run.verdict,
        "quality": run.quality,
        "latency": run.latency,
        "llm_call_count": run.llm_call_count,
        "total_tokens": run.total_tokens,
        "cost_usd": run.cost_usd,
        "retried": run.retried,
        "needs_human": run.needs_human,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "routing_path": run.routing_path,
    }


class PollHub:
    """One poll loop broadcasting snapshots to all connected clients."""

    def __init__(
        self,
        source: LangfuseSource,
        *,
        interval: float = 3.0,
        window: float = 6 * 3600,
        limit: int = 100,
    ) -> None:
        self.source = source
        self.interval = interval
        self.window = window
        self.limit = limit
        self.clients: set[WebSocket] = set()
        self.snapshot: list[dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            log.info("poller started (interval=%ss window=%ss)", self.interval, self.window)

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.add(ws)
        await ws.send_json({"type": "snapshot", "runs": self.snapshot})

    def disconnect(self, ws: WebSocket) -> None:
        self.clients.discard(ws)

    async def _run(self) -> None:
        while not self._stop.is_set():
            try:
                runs = await asyncio.to_thread(self._fetch)
                self.snapshot = runs
                payload = {"type": "snapshot", "runs": runs}
                dead: list[WebSocket] = []
                for ws in list(self.clients):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    self.clients.discard(ws)
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("poller iteration failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass

    def _fetch(self) -> list[dict[str, Any]]:
        since = datetime.now() - timedelta(seconds=self.window)
        try:
            runs = list_recent_runs(self.source, since=since, limit=self.limit)
        except Exception as exc:
            log.warning("langfuse fetch failed: %s", exc)
            return self.snapshot
        return [floor_payload(r) for r in runs]
