"""Langfuse-derived snapshot cache — never fabricated rows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient

from mailroom_ui.langfuse_source import LangfuseSource
from mailroom_ui.trace_cache import (
    CACHE_SOURCE,
    persist_floor,
    persist_run,
    snapshot_bundle,
)
from server.main import create_app, _desk_runs
from server.poller import PollHub
from mailroom_ui.sources import TraceSourceUnavailable
from tests.fake_langfuse import FakeClient, make_trace


class _DeadClient:
    api = None


def _down_source():
    return LangfuseSource(client=_DeadClient())


def test_snapshot_export_is_empty_not_canned():
    bundle = snapshot_bundle()
    assert bundle["source"] == CACHE_SOURCE
    assert bundle["traces"]["runs"] == []


def test_warm_cache_does_not_reopen_live_display_when_langfuse_down():
    persist_floor(
        [{"trace_id": "t-cached", "filename": "kept.pdf", "stage": "archived"}],
        source="langfuse",
    )
    persist_run("t-cached", {
        "trace_id": "t-cached",
        "filename": "kept.pdf",
        "spans": [],
        "generations": [],
        "scores": {},
    })
    with TestClient(create_app(_down_source())) as c:
        listing = c.get("/api/traces?since=3600")
        assert listing.status_code == 503
        assert c.get("/api/traces/t-cached").status_code == 503
        health = c.get("/api/health").json()
        assert health["ok"] is False
        assert health["source"] != CACHE_SOURCE
        assert health["cache"]["has_snapshot"] is True
        snap = c.get("/api/snapshot").json()
        assert snap["traces"]["runs"][0]["trace_id"] == "t-cached"


def test_empty_cache_and_langfuse_down_stays_closed():
    with TestClient(create_app(_down_source())) as c:
        listing = c.get("/api/traces?since=3600")
        assert listing.status_code == 503
        health = c.get("/api/health").json()
        assert health.get("langfuse") is False
        assert health.get("source") != CACHE_SOURCE or not health.get("cache", {}).get("has_snapshot")


def test_live_traces_still_hit_langfuse():
    now = datetime.now(timezone.utc) - timedelta(minutes=10)
    src = LangfuseSource(client=FakeClient([make_trace("t-live", filename="live.pdf", base_time=now)]))
    with TestClient(create_app(src)) as c:
        listing = c.get("/api/traces?since=3600").json()
        assert listing["source"] == "langfuse"
        assert listing["runs"][0]["filename"] == "live.pdf"
        assert listing["runs"][0]["primary_outcome"]


def test_aggregate_desks_reject_warm_hub_rows_after_outage(monkeypatch):
    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    src = LangfuseSource(client=FakeClient([make_trace("warm", base_time=now)]), cache_ttl=0)
    hub = PollHub(src)
    assert hub._fetch()
    hub.stale = False
    assert _desk_runs(src, hub, since_seconds=3600, limit=100)[0].trace_id == "warm"

    def unavailable(**kwargs):
        raise TraceSourceUnavailable("test outage")

    monkeypatch.setattr(src, "list_traces", unavailable)
    hub.stale = True
    with pytest.raises(TraceSourceUnavailable):
        _desk_runs(src, hub, since_seconds=3600, limit=100)


@pytest.mark.parametrize("path", ["/api/sessions/MATTER-001", "/v1/ops/status", "/v1/ops/throughput", "/v1/ops/distribution"])
def test_session_and_operator_reads_reject_stale_hub_rows(monkeypatch, path):
    from server import main
    from operator_desk.auth import create_access_token

    now = datetime.now(timezone.utc) - timedelta(minutes=5)
    src = LangfuseSource(client=FakeClient([make_trace("warm", base_time=now)]), cache_ttl=0)
    hub = PollHub(src)
    assert hub._fetch()
    hub.stale = False
    monkeypatch.setattr(main, "PollHub", lambda *args, **kwargs: hub)
    client = TestClient(main.create_app(src))
    headers = {"Authorization": "Bearer " + create_access_token("fixture", "viewer")}
    assert client.get(path, headers=headers).status_code == 200

    def unavailable(**kwargs):
        raise TraceSourceUnavailable("test outage")

    monkeypatch.setattr(src, "list_traces", unavailable)
    hub.stale = True
    assert client.get(path, headers=headers).status_code == 503
