from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from mailroom_ui.langfuse_source import LangfuseSource, LangfuseUnavailable, list_recent_runs
from mailroom_ui.models import PipelineRun
from tests.fake_langfuse import FakeClient, make_trace


def _source(traces, cache_ttl=0, poll_cache_ttl=0):
    return LangfuseSource(client=FakeClient(traces), cache_ttl=cache_ttl, poll_cache_ttl=poll_cache_ttl)


def test_list_traces_returns_dicts():
    src = _source([make_trace("t1"), make_trace("t2")])
    traces = src.list_traces()
    assert len(traces) == 2
    assert traces[0]["id"] == "t1"


def test_get_run_full():
    src = _source([make_trace("t1")])
    run = src.get_run("t1")
    assert run is not None
    assert run.trace_id == "t1"
    assert run.generations[0].model == "qwen/qwen3.7-flash"


def test_get_run_missing():
    src = _source([])
    assert src.get_run("nope") is None


def test_list_recent_runs_newest_first():
    base = datetime(2026, 1, 1, 12, 0, 0)
    t_old = make_trace("t-old", base_time=base - timedelta(hours=5))
    t_new = make_trace("t-new", base_time=base)
    src = _source([t_old, t_new])
    runs = list_recent_runs(src, since=base - timedelta(hours=6), limit=10)
    assert [r.trace_id for r in runs] == ["t-new", "t-old"]


def test_sessions():
    src = _source([make_trace("t1", matter_id="M-1"), make_trace("t2", matter_id="M-2")])
    sessions = src.list_sessions()
    assert len(sessions) == 2
    traces = src.get_session_traces("M-1")
    assert len(traces) == 1


def test_list_traces_name_filter_passed_to_client():
    src = _source([make_trace("t1"), make_trace("t2", stage="processing")])
    src.list_traces(name="document-pipeline")
    call = src.client.api.trace.calls[-1]
    assert call["name"] == "document-pipeline"


def test_list_traces_tags_and_environments_passed():
    src = _source([make_trace("t1")])
    src.list_traces(tags=["mailroom", "live"], environments=["pilot"])
    call = src.client.api.trace.calls[-1]
    assert call["tags"] == "mailroom,live"
    assert call["environment"] == "pilot"


def test_list_traces_since_passed():
    base = datetime(2026, 1, 1, 12, 0, 0)
    src = _source([make_trace("t1")])
    src.list_traces(since=base)
    assert src.client.api.trace.calls[-1]["from_timestamp"] == base


def test_list_recent_runs_filters_to_pipeline_traces():
    src = _source([make_trace("t1"), make_trace("t2", stage="processing")])
    src.client.traces.append(
        {"id": "other", "name": "ingest-log", "updated_at": datetime(2026, 1, 1, 12, 0, 0)}
    )
    runs = list_recent_runs(src, since=datetime(2025, 1, 1), limit=10)
    assert {r.trace_id for r in runs} == {"t1", "t2"}


def test_cache_avoids_requery_within_ttl():
    src = _source([make_trace("t1")], cache_ttl=60, poll_cache_ttl=60)
    src.list_traces()
    src.list_traces()
    assert len(src.client.api.trace.calls) == 1


def test_cache_expires():
    src = _source([make_trace("t1")], cache_ttl=-1, poll_cache_ttl=-1)
    src.list_traces()
    src.list_traces()
    assert len(src.client.api.trace.calls) == 2


def test_unavailable_raises_when_client_has_no_api():
    src = LangfuseSource(client=object())
    with pytest.raises(LangfuseUnavailable):
        src.list_traces()
    assert src.health()["langfuse"] is False


def test_get_run_caches_full_detail():
    src = _source([make_trace("t1")], cache_ttl=60, poll_cache_ttl=60)
    first = src.get_run("t1")
    second = src.get_run("t1")
    assert first == second
    assert first.trace_id == "t1"


def test_health_reports_ok_and_down():
    assert _source([make_trace("t1")]).health()["langfuse"] is True
    assert LangfuseSource(client=object()).health()["langfuse"] is False


def test_list_recent_runs_returns_pipeline_runs():
    src = _source([make_trace("t1")])
    runs = list_recent_runs(src, since=datetime(2025, 1, 1), limit=5)
    assert all(isinstance(r, PipelineRun) for r in runs)


class TestScoreContaminationFix:
    """V-2: the v1 scores fallback ignored trace_id on Langfuse v4 and returned
    OTHER traces' scores. Empty-v3 must be treated as empty."""

    def test_empty_v3_does_not_fallback_to_v1(self):
        from mailroom_ui.langfuse_source import LangfuseSource
        from tests.fake_langfuse import FakeClient, Obj

        class V3Empty:
            def get_many_v3(self, trace_id, limit=100):
                return Obj(data=[])

        class V1Poisoned:
            # The v1 endpoint ignores trace_id — would return other traces' scores.
            def get_many(self, trace_id, limit=100):
                return Obj(data=[{"name": "mailroom-pipeline-judge", "value": "CORRECT"}])

        client = FakeClient()
        client.api.scores_v3 = V3Empty()
        client.api.scores = V1Poisoned()
        src = LangfuseSource(client=client)
        scores = src.get_scores("some-trace")
        assert scores == []  # no cross-trace contamination

    def test_v3_scores_used_when_present(self):
        from mailroom_ui.langfuse_source import LangfuseSource
        from tests.fake_langfuse import FakeClient, Obj

        class V3Ok:
            def get_many_v3(self, trace_id, limit=100):
                return Obj(data=[{"name": "stage_completed", "value": 1}])

        client = FakeClient()
        client.api.scores_v3 = V3Ok()
        src = LangfuseSource(client=client)
        scores = src.get_scores("t1")
        assert len(scores) == 1
        assert scores[0]["name"] == "stage_completed"


class TestPollerPartialFailure:
    """V-4: a Langfuse fetch failure returns None (keep last good snapshot)
    instead of [] (wiping the floor)."""

    def test_fetch_failure_returns_none_not_empty(self):
        import asyncio
        from unittest.mock import patch

        from server.poller import PollHub

        src = object()
        hub = PollHub(src, interval=60, window=21600, limit=100)
        with patch("server.poller.list_recent_runs", side_effect=RuntimeError("langfuse down")):
            assert hub._fetch() is None

    def test_fetch_success_returns_runs(self):
        from unittest.mock import patch

        from server.poller import PollHub

        src = object()
        hub = PollHub(src, interval=60, window=21600, limit=100)
        with patch("server.poller.list_recent_runs", return_value=[]):
            assert hub._fetch() == []
