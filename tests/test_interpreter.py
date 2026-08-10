from __future__ import annotations

from datetime import datetime, timedelta

from mailroom_ui.models import Phase, Stage
from mailroom_ui.trace_interpreter import (
    build_routing_path,
    derive_stage,
    interpret_trace,
)
from tests.fake_langfuse import FakeClient, make_trace


def _run(trace: dict):
    return interpret_trace(
        trace,
        trace.get("observations", []),
        trace.get("scores", []),
    )


def test_archived_run_full():
    trace = make_trace("t-archived")
    run = _run(trace)
    assert run.trace_id == "t-archived"
    assert run.stage == Stage.ARCHIVED
    assert run.phase == Phase.TERMINAL
    assert run.doc_type == "contract"
    assert run.matter_id == "MATTER-001"
    assert run.session_id == "MATTER-001"
    assert run.classification_confidence == 0.98
    assert run.extraction_confidence == 0.91
    assert run.verdict == "CORRECT"
    assert run.quality == 0.9
    assert run.llm_call_count == 2
    assert run.total_tokens == 4600
    assert run.cost_usd == 0.00055
    assert len(run.spans) == 6
    assert run.routing_path == [
        "ingest",
        "classify",
        "extract",
        "report",
        "catalog",
        "archive",
    ]
    assert run.needs_human is False


def test_review_stage():
    trace = make_trace(
        "t-review",
        stage="review",
        span_names=["ingest-document", "classify-document", "route-for-review"],
        verdict=None,
        quality=None,
    )
    run = _run(trace)
    assert run.stage == Stage.HUMAN_REVIEW
    assert run.phase == Phase.REVIEW
    assert run.needs_human is True


def test_failed_stage():
    trace = make_trace("t-failed", stage="failed", verdict=None)
    run = _run(trace)
    assert run.stage == Stage.FAILED
    assert run.phase == Phase.TERMINAL


def test_retry_detection():
    trace = make_trace(
        "t-retry",
        span_names=[
            "ingest-document",
            "classify-document",
            "classify-document",
            "extract-fields",
            "extract-fields",
            "compile-report",
        ],
    )
    run = _run(trace)
    assert "retry_classify" in run.routing_path
    assert "retry_extract" in run.routing_path
    assert run.retried is True


def test_in_flight_derives_stage_from_last_span():
    trace = make_trace(
        "t-inflight",
        stage="processing",
        span_names=["ingest-document", "classify-document"],
        verdict=None,
    )
    run = _run(trace)
    assert run.stage in (Stage.CLASSIFY, Stage.INGEST)
    assert run.phase == Phase.INTAKE_SORT


def test_derive_stage_output_wins():
    trace = make_trace("t-x", stage="review")
    run = _run(trace)
    assert derive_stage(trace["output"], run.spans) == Stage.HUMAN_REVIEW


def test_light_interpretation_from_list_response():
    trace = make_trace("t-light", stage="archived")
    run = interpret_trace(trace)  # observations/scores embedded in trace dict
    assert run.stage == Stage.ARCHIVED
    assert run.spans and run.generations
