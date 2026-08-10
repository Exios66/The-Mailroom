"""TUI console tests: banner/table building from payloads (no live server)."""

from collections import deque

from rich.console import Console

from tui.mailroom_console import (
    STATION_BY_STAGE,
    banner,
    floor_table,
    inspect_panels,
    metrics_table,
    review_table,
    runs_to_banners,
)

RUN = {
    "trace_id": "demo-x",
    "filename": "contract_03_service_agreement.pdf",
    "stage": "archived",
    "doc_type": "contract",
    "classification_confidence": 0.98,
    "extraction_confidence": 0.96,
    "verdict": "CORRECT",
    "quality": 0.97,
    "cost_usd": 0.0496,
    "routing_path": ["ingest", "classify", "extract", "report", "catalog", "archive"],
}


def render(renderable) -> str:
    console = Console(width=120, force_terminal=True, record=True)
    console.print(renderable)
    return console.export_text()


def test_banner_format():
    assert banner("Sorter") == "*** Beginning station: Sorter ***"
    assert banner("Review siding", "Moving to") == "*** Moving to station: Review siding ***"


def test_runs_to_banners_arrival_and_advance():
    log = deque()
    runs_to_banners({}, [RUN], log)
    assert any("Entering station: Archive" in line for line in log)

    advanced = dict(RUN, stage="review", verdict="PARTIAL")
    runs_to_banners({RUN["trace_id"]: RUN}, [advanced], log)
    assert any("Moving to station: Review siding" in line for line in log)
    assert any("Judge verdict: PARTIAL" in line for line in log)


def test_floor_table_renders():
    table = floor_table([RUN])
    text = render(table)
    assert "contract_03_service_agreement.pdf" in text
    assert "CORRECT" in text
    assert "$0.0496" in text


def test_review_table_renders():
    table = review_table([dict(RUN, stage="review", escalation_reason="low confidence")])
    assert "low confidence" in render(table)


def test_metrics_table_renders():
    table = metrics_table({"total_docs": 10, "verdict_counts": {"CORRECT": 3, "PARTIAL": 1}})
    text = render(table)
    assert "10" in text
    assert "verdict CORRECT" in text


def test_inspect_panels_build():
    run = dict(
        RUN,
        spans=[{"name": "ingest-document", "status": "SUCCESS", "latency": 3.2}],
        generations=[{"name": "classify-document", "model": "gpt-4o-mini",
                      "usage_input_tokens": 400, "usage_output_tokens": 700,
                      "cost_usd": 0.0005, "latency": 6.1}],
        scores={"mailroom-pipeline-judge": "CORRECT"},
    )
    panels = inspect_panels(run)
    assert len(panels) == 4
    text = "\n".join(render(p) for p in panels)
    assert "ingest-document" in text
    assert "gpt-4o-mini" in text
    assert "mailroom-pipeline-judge" in text


def test_station_map_covers_stages():
    for stage in ("ingest", "classify", "extract", "boss", "review", "report",
                  "catalog", "archive", "archived", "failed"):
        assert stage in STATION_BY_STAGE
