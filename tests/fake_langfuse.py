"""Fake Langfuse client — deterministic in-memory data, no network."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def model_dump(self, mode="python"):
        out = {}
        for k, v in self.__dict__.items():
            if isinstance(v, datetime):
                v = v.isoformat()
            out[k] = v
        return out


def make_trace(
    trace_id: str,
    *,
    filename: str = "sample.txt",
    matter_id: str = "MATTER-001",
    environment: str = "pilot",
    tags: list[str] | None = None,
    stage: str = "archived",
    doc_type: str = "contract",
    class_conf: float = 0.98,
    extract_conf: float = 0.91,
    span_names: list[str] | None = None,
    session_id: str | None = None,
    attempt: int = 0,
    verdict: str | None = "CORRECT",
    quality: float | None = 0.9,
    latency: float = 12.5,
    base_time: datetime | None = None,
) -> dict:
    base_time = base_time or datetime(2026, 1, 1, 12, 0, 0)
    span_names = span_names or [
        "ingest-document",
        "classify-document",
        "extract-fields",
        "compile-report",
        "write-catalog",
        "archive-document",
    ]
    obs = []
    for i, name in enumerate(span_names):
        obs.append(
            Obj(
                id=f"span-{trace_id}-{i}",
                type="SPAN",
                name=name,
                start_time=base_time + timedelta(seconds=10 * i),
                end_time=base_time + timedelta(seconds=10 * i + 8),
                latency=8.0,
                level="DEFAULT",
                input={"doc_id": filename},
                output={"stage": "ok"},
            )
        )
    obs.append(
        Obj(
            id=f"gen-{trace_id}-0",
            type="GENERATION",
            name="classify-document",
            model="qwen/qwen3.7-flash",
            start_time=base_time + timedelta(seconds=11),
            end_time=base_time + timedelta(seconds=20),
            latency=9.0,
            input={"messages": "..."},
            output="contract",
            usage={"total": 1200, "input": 1000, "output": 200},
            cost_details={"total": 0.00015},
            level="DEFAULT",
        )
    obs.append(
        Obj(
            id=f"gen-{trace_id}-1",
            type="GENERATION",
            name="extract-fields",
            model="qwen/qwen3.7-flash",
            start_time=base_time + timedelta(seconds=21),
            end_time=base_time + timedelta(seconds=40),
            latency=19.0,
            input={"messages": "..."},
            output='{"parties": ["Acme Corp"]}',
            usage={"total": 3400, "input": 3000, "output": 400},
            cost_details={"total": 0.0004},
            level="DEFAULT",
        )
    scores = [
        Obj(name="classification_confidence", value=class_conf, data_type="NUMERIC"),
        Obj(name="extraction_confidence", value=extract_conf, data_type="NUMERIC"),
        Obj(name="stage_completed", value=stage == "archived", data_type="BOOLEAN"),
        Obj(name="estimated_cost_usd", value=0.00055, data_type="NUMERIC"),
        Obj(name="total_tokens", value=4600, data_type="NUMERIC"),
    ]
    if verdict:
        scores.append(Obj(name="mailroom-pipeline-judge", value=verdict, data_type="CATEGORICAL"))
    if quality is not None:
        scores.append(Obj(name="mailroom-pipeline-quality", value=quality, data_type="NUMERIC"))
    return {
        "id": trace_id,
        "name": "document-pipeline",
        "timestamp": base_time,
        "updated_at": base_time + timedelta(seconds=80),
        "latency": latency,
        "session_id": session_id or matter_id,
        "environment": environment,
        "tags": tags or ["mailroom", environment],
        "metadata": {"pipeline": "mailroom", "attempt": attempt},
        "input": {"filename": filename, "matter_id": matter_id, "attempt": attempt},
        "output": {
            "stage": stage,
            "doc_type": doc_type,
            "classification_confidence": class_conf,
            "extraction_confidence": extract_conf,
        },
        "observations": obs,
        "scores": scores,
    }


@dataclass
class FakeList:
    data: list = field(default_factory=list)


class FakeTraceApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def list(self, **kw):
        return FakeList(data=self.traces)

    def get(self, trace_id: str):
        for t in self.traces:
            if t["id"] == trace_id:
                return Obj(**t)
        return None


class FakeObservationsApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def get_many(self, trace_id: str, **kw):
        for t in self.traces:
            if t["id"] == trace_id:
                return FakeList(data=t.get("observations", []))
        return FakeList(data=[])


class FakeScoresApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def get_many(self, trace_id: str, **kw):
        for t in self.traces:
            if t["id"] == trace_id:
                return FakeList(data=t.get("scores", []))
        return FakeList(data=[])


class FakeSessionsApi:
    def __init__(self, traces: list[dict]):
        self.traces = traces

    def list(self, limit=100):
        seen = {}
        for t in self.traces:
            sid = t.get("session_id") or "DEFAULT"
            seen.setdefault(sid, {"id": sid, "name": sid})
            seen[sid]["created_at"] = t["timestamp"]
            seen[sid]["updated_at"] = t["updated_at"]
        return FakeList(data=list(seen.values()))

    def get(self, session_id: str, limit=100):
        return FakeList(data=[t for t in self.traces if (t.get("session_id") or "DEFAULT") == session_id])


class FakeClient:
    def __init__(self, traces: list[dict] | None = None):
        self.traces = traces or []
        self.api = Obj(
            trace=FakeTraceApi(self.traces),
            observations=FakeObservationsApi(self.traces),
            scores=FakeScoresApi(self.traces),
            sessions=FakeSessionsApi(self.traces),
        )
