"""Langfuse adapter — the sole source of truth for The-Mailroom.

Every function here reads Langfuse API data only. The interface never falls
back to locally fabricated data: if Langfuse is unreachable, callers get an
empty result + healthy error so the UI can say "MAILROOM CLOSED".

Works with langfuse SDK >= 2.50 (both the v2/v3 `api.*` surface and the
core `Langfuse(...)` client). Attribute guards keep it version-tolerant.
"""

from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from .models import PipelineRun
from .trace_interpreter import interpret_trace


class LangfuseUnavailable(RuntimeError):
    pass


class TTLCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            hit = self._data.get(key)
            if hit is None:
                return None
            expires, value = hit
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def _to_dict(obj: Any) -> Any:
    """Pydantic SDK models -> plain dict; pass dicts through."""
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    return obj


def _page_data(response: Any) -> list[Any]:
    """Paginated API responses: pull the `.data` list defensively."""
    if response is None:
        return []
    data = getattr(response, "data", None)
    if isinstance(data, list):
        return data
    if isinstance(response, list):
        return response
    return []


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


class LangfuseSource:
    """Read-only gateway to one Langfuse project."""

    def __init__(
        self,
        client: Any = None,
        *,
        cache_ttl: float = 2.0,
        poll_cache_ttl: float = 1.0,
    ) -> None:
        self.client = client if client is not None else self._build_client()
        self.available = self.client is not None
        self.cache = TTLCache()
        self.cache_ttl = cache_ttl
        self.poll_cache_ttl = poll_cache_ttl

    # ---------------------------------------------------------------- client

    @staticmethod
    def _build_client() -> Any:
        try:
            import langfuse  # noqa: F401
        except ImportError:
            return None
        from langfuse import Langfuse

        try:
            return Langfuse(
                public_key=os.environ.get("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                host=os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
            )
        except Exception:
            return None

    def _api(self, resource: str) -> Any:
        if not self.available:
            raise LangfuseUnavailable("no Langfuse client")
        api = getattr(self.client, "api", None)
        if api is None:
            raise LangfuseUnavailable("client.api unavailable")
        return getattr(api, resource, None)

    def _guarded(self, label: str, fn: Callable[[], Any]) -> Any:
        """Any Langfuse API failure surfaces as LangfuseUnavailable — the
        documented contract for callers (never stale, never fabricated)."""
        try:
            return fn()
        except LangfuseUnavailable:
            raise
        except Exception as exc:
            raise LangfuseUnavailable(f"{label}: {str(exc)[:200]}") from exc

    # ----------------------------------------------------------------- traces

    def list_traces(
        self,
        *,
        since: Optional[datetime] = None,
        limit: int = 200,
        tags: Optional[list[str]] = None,
        environments: Optional[list[str]] = None,
        name: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Raw trace summaries (list page)."""
        key = f"traces:{since}:{limit}:{tags}:{environments}:{name}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        trace_api = self._api("trace")
        if trace_api is None:
            raise LangfuseUnavailable("trace API unavailable")
        kw: dict[str, Any] = {"limit": limit}
        if since is not None:
            kw["from_timestamp"] = since
        if tags:
            kw["tags"] = ",".join(tags)
        if environments:
            kw["environment"] = ",".join(environments)
        if name:
            kw["name"] = name
        resp = self._guarded(f"trace.list", lambda: trace_api.list(**kw))
        out = [_to_dict(t) for t in _page_data(resp)]
        self.cache.set(key, out, self.poll_cache_ttl)
        return out

    def get_trace(self, trace_id: str) -> Optional[dict[str, Any]]:
        key = f"trace:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        trace_api = self._api("trace")
        if trace_api is None:
            raise LangfuseUnavailable("trace API unavailable")
        try:
            resp = trace_api.get(trace_id)
        except Exception:
            return None
        if resp is None:
            return None
        out = _to_dict(resp)
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_observations(self, trace_id: str) -> list[dict[str, Any]]:
        key = f"obs:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        # The trace record embeds its own authoritative observation set
        # (complete: usage, cost, model, io) — one API call instead of two.
        embedded = (self.get_trace(trace_id) or {}).get("observations")
        if isinstance(embedded, list) and embedded:
            out = [_to_dict(o) for o in embedded]
        else:
            # Fallback: the v2 observations index (eventually consistent).
            obs_api = self._api("observations")
            if obs_api is None:
                return []
            resp = self._guarded("observations.get_many",
                                 lambda: obs_api.get_many(trace_id=trace_id, limit=100))
            out = [_to_dict(o) for o in _page_data(resp)]
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_scores(self, trace_id: str) -> list[dict[str, Any]]:
        key = f"scores:{trace_id}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        # v3 scores endpoint: trace filter works and CATEGORICAL values come
        # back label-resolved. The v1 endpoint ignores `trace_id` on Langfuse
        # v4 (returns global pages) — never use it as the primary read.
        v3 = getattr(self.client, "api", None) and getattr(self.client.api, "scores_v3", None)
        out: list[dict[str, Any]] = []
        if v3 is not None:
            try:
                resp = self._guarded("scores.get_many_v3",
                                     lambda: v3.get_many_v3(trace_id=trace_id, limit=100))
                out = [_to_dict(o) for o in _page_data(resp)]
            except LangfuseUnavailable:
                out = []
        if not out:
            scores_api = self._api("scores")
            if scores_api is None:
                return []
            resp = self._guarded("scores.get_many",
                                 lambda: scores_api.get_many(trace_id=trace_id, limit=100))
            out = [_to_dict(o) for o in _page_data(resp)]
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_score_configs(self) -> dict[str, dict[str, Any]]:
        """Project score configs: name -> {"data_type", "categories"}.

        Used to resolve CATEGORICAL score values (judge verdicts) back to
        their labels. Cached at process level.
        """
        key = "score-configs"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        out: dict[str, dict[str, Any]] = {}
        try:
            cfg_api = self._api("score_configs")
            if cfg_api is not None:
                resp = cfg_api.get()
                for cfg in _page_data(resp):
                    d = _to_dict(cfg)
                    name = d.get("name")
                    if not name:
                        continue
                    cats = []
                    for cat in d.get("categories") or []:
                        if isinstance(cat, dict) and cat.get("label") is not None:
                            cats.append({"value": cat.get("value"), "label": cat.get("label")})
                    out[name] = {"data_type": d.get("data_type"), "categories": cats}
        except Exception:
            out = {}
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_run(self, trace_id: str) -> Optional[PipelineRun]:
        """Full interpreted pipeline run for one trace (sole source: Langfuse)."""
        trace = self.get_trace(trace_id)
        if trace is None:
            return None
        obs = self.get_observations(trace_id)
        scores = self.get_scores(trace_id)
        return interpret_trace(trace, obs, scores, score_configs=self.get_score_configs())

    # --------------------------------------------------------------- sessions

    def list_sessions(self, limit: int = 100) -> list[dict[str, Any]]:
        key = f"sessions:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        sessions_api = self._api("sessions")
        if sessions_api is None:
            return []
        resp = self._guarded("sessions.list",
                             lambda: sessions_api.list(limit=limit))
        out = [_to_dict(s) for s in _page_data(resp)]
        self.cache.set(key, out, self.cache_ttl)
        return out

    def get_session_traces(self, session_id: str, limit: int = 100) -> list[dict[str, Any]]:
        key = f"session-traces:{session_id}:{limit}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        try:
            resp = self._guarded("sessions.get",
                                 lambda: self._api("sessions").get(session_id, limit=limit))
        except LangfuseUnavailable:
            return []
        out = [_to_dict(t) for t in _page_data(resp)]
        self.cache.set(key, out, self.cache_ttl)
        return out

    # ---------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        """Live Langfuse reachability: real API call, no cache (must be fresh)."""
        try:
            self.list_traces(limit=1)
            ok = True
        except Exception:
            ok = False
        return {"langfuse": ok, "source": "langfuse", "cached_trace_count": None}


def list_recent_runs(
    source: LangfuseSource,
    *,
    since: Optional[datetime] = None,
    limit: int = 200,
) -> list[PipelineRun]:
    """Convenience: recent traces -> interpreted runs, newest first.

    Uses the trace-list response only (light runs) — cheap enough to poll.
    Fetches score configs so CATEGORICAL verdicts can be label-resolved.
    Also fetches scores per trace so verdicts/qualities surface in light runs.
    """
    since = since or (datetime.now() - timedelta(hours=6))
    traces = source.list_traces(since=since, limit=limit, name="document-pipeline")
    score_configs = source.get_score_configs()
    runs = []
    for t in traces:
        tid = t.get("id")
        if not tid:
            continue
        scores = source.get_scores(tid)
        runs.append(interpret_trace(t, scores=scores, score_configs=score_configs))
    runs.sort(key=lambda r: r.updated_at or datetime.min, reverse=True)
    return runs
