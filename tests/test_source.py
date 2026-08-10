from __future__ import annotations

from datetime import datetime, timedelta

from mailroom_ui.langfuse_source import LangfuseSource, list_recent_runs
from tests.fake_langfuse import FakeClient, make_trace


def _source(traces):
    return LangfuseSource(client=FakeClient(traces), cache_ttl=0)


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
