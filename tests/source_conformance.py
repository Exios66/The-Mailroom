"""Trace-source conformance kit (ADR-006, T-5).

A *golden document trace* is written once, backend-neutral: a root plus node
spans and LLM calls, named by the pipeline contract. Each registered source
adapter supplies a renderer that turns it into that backend's raw shape and a
source over a fake client. Conformance means every adapter interprets the same
golden trace into the same ``PipelineRun`` (``run_fingerprint``).

Adding a backend: register the adapter (``source_registry.register_source``),
add a renderer + fake below (or in the plugin's own tests, calling
``assert_conformant``), and the floor will display it like any other sink.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from mailroom_ui.models import PipelineRun
from mailroom_ui.pipeline_schema import CONTRACT, observation_type_for

BASE = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class GoldenSpan:
    name: str
    start: float                     # seconds after the root start
    duration: float
    input: dict[str, Any] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    # LLM call fields (a generation, not a node)
    model: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0

    @property
    def is_llm(self) -> bool:
        return self.model is not None


@dataclass
class GoldenTrace:
    trace_id: str
    input: dict[str, Any]
    output: dict[str, Any]
    spans: list[GoldenSpan]
    scores: dict[str, Any] = field(default_factory=dict)
    session_id: str = "MATTER-GOLD"
    environment: str = "pilot"
    tags: tuple[str, ...] = ("mailroom", "pilot")
    duration: float = 60.0


def _node(name: str, start: float, **kw: Any) -> GoldenSpan:
    return GoldenSpan(name, start, kw.pop("duration", 4.0), input={"doc_id": "gold.txt"}, **kw)


GOLDEN_TRACES: list[GoldenTrace] = [
    GoldenTrace(
        "gold-archived",
        input={"filename": "gold.txt", "matter_id": "MATTER-GOLD", "attempt": 0},
        output={
            "stage": "archived", "doc_type": "contract", "doc_subclass": "license",
            "classification_confidence": 0.98, "extraction_confidence": 0.93,
        },
        spans=[
            _node("intake-document", 0, output={"stage": "ok"}),
            _node("normalize-intake", 5, output={"messy": False, "changed": True, "method": "rules"}),
            _node("classify-document", 10, output={"doc_type": "contract"}),
            GoldenSpan("classify-document", 11, 3, input={"messages": "..."}, output={"doc_type": "contract"},
                       model="qwen/qwen3.7-flash", tokens_in=1000, tokens_out=200, cost=0.00015),
            _node("extract-fields", 15, output={"stage": "ok"}),
            GoldenSpan("extract-fields", 16, 6, input={"messages": "..."}, output={"parties": ["Acme"]},
                       model="qwen/qwen3.7-flash", tokens_in=3000, tokens_out=400, cost=0.0004),
            _node("compile-report", 25),
            _node("write-catalog", 30),
            _node("archive-document", 35),
        ],
        scores={
            "classification_confidence": 0.98, "extraction_confidence": 0.93,
            "total_tokens": 4600, "estimated_cost_usd": 0.00055,
        },
    ),
    GoldenTrace(
        "gold-review",
        input={"filename": "dispute.pdf", "matter_id": "MATTER-GOLD", "attempt": 0},
        output={
            "stage": "review", "doc_type": "correspondence", "doc_subclass": "demand",
            "classification_confidence": 0.71, "extraction_confidence": 0.62,
            "escalation_reason": "sorter and reviewer disagree",
        },
        spans=[
            _node("intake-document", 0),
            _node("transcribe-pdf", 4),
            _node("classify-document", 8, output={"doc_type": "correspondence"}),
            _node("classify-document", 12, output={"doc_type": "contract"}),
            _node("arbitrate-classification", 16, output={"doc_type": "correspondence"}),
            _node("extract-fields", 20),
            _node("judge-verify", 26, output={"verdict": "ambiguous"}),
            _node("arbitrate-verdict", 30),
            _node("route-for-review", 34),
        ],
        scores={"classification_confidence": 0.71, "extraction_confidence": 0.62},
    ),
    GoldenTrace(
        "gold-aborted",
        input={"filename": "slow.txt", "matter_id": "MATTER-GOLD", "attempt": 1},
        output={
            "stage": "failed", "doc_type": "insurance_claim",
            "run_aborted": True, "failure_class": "llm_timeout",
            "error_message": "run aborted [llm_timeout]: provider did not answer",
        },
        spans=[
            _node("intake-document", 0),
            _node("classify-document", 5, output={"doc_type": "insurance_claim"}),
            _node("extract-fields", 10, error="run aborted [llm_timeout]: provider did not answer"),
        ],
        scores={"run_aborted": 1},
    ),
]


# ---------------------------------------------------------------- renderers


def render_langfuse(golden: GoldenTrace) -> Any:
    from mailroom_ui.langfuse_source import LangfuseSource
    from tests.fake_langfuse import FakeClient, Obj

    t0 = BASE
    obs = [
        Obj(
            id=f"{golden.trace_id}-root", type="CHAIN", name=CONTRACT["trace_name"],
            isRootObservation=True, start_time=t0, end_time=t0 + timedelta(seconds=golden.duration),
            latency=golden.duration, level="DEFAULT", input=golden.input, output=golden.output,
        )
    ]
    for i, s in enumerate(golden.spans):
        start = t0 + timedelta(seconds=s.start)
        common = dict(
            id=f"{golden.trace_id}-{i}", name=s.name, start_time=start,
            end_time=start + timedelta(seconds=s.duration), latency=s.duration,
            input=s.input, output=s.output,
            level="ERROR" if s.error else "DEFAULT", status_message=s.error,
        )
        if s.is_llm:
            obs.append(Obj(type="GENERATION", model=s.model,
                           usage={"input": s.tokens_in, "output": s.tokens_out,
                                  "total": s.tokens_in + s.tokens_out},
                           cost_details={"total": s.cost}, **common))
        else:
            obs.append(Obj(type=observation_type_for(s.name).upper(), **common))
    scores = [
        Obj(name=k, value=v, data_type="CATEGORICAL" if isinstance(v, str) else "NUMERIC")
        for k, v in golden.scores.items()
    ]
    trace = {
        "id": golden.trace_id, "name": CONTRACT["trace_name"], "timestamp": t0,
        "updated_at": t0 + timedelta(seconds=golden.duration), "latency": golden.duration,
        "session_id": golden.session_id, "environment": golden.environment,
        "user_id": None, "release": None, "tags": list(golden.tags),
        "metadata": {"pipeline": "mailroom", "attempt": golden.input.get("attempt")},
        "input": golden.input, "output": golden.output,
        "observations": obs, "scores": scores,
    }
    return LangfuseSource(client=FakeClient([trace]))


def render_phoenix(golden: GoldenTrace) -> Any:
    from mailroom_ui.phoenix_source import PhoenixSource
    from tests.fake_phoenix import FakePhoenixClient, make_phoenix_span

    root_id = f"{golden.trace_id}-root"
    root_attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        "input.value": json.dumps(golden.input),
        "output.value": json.dumps(golden.output),
        "session.id": golden.session_id,
        "mailroom.tags": ",".join(golden.tags),
        "mailroom.environment": golden.environment,
        **{f"mailroom.score.{k}": v for k, v in golden.scores.items()},
    }
    spans = [make_phoenix_span(CONTRACT["trace_name"], golden.trace_id, root_id,
                               start_time=BASE, duration_s=golden.duration, attributes=root_attrs)]
    for i, s in enumerate(golden.spans):
        attrs: dict[str, Any] = {
            "openinference.span.kind": "LLM" if s.is_llm else "CHAIN",
            "input.value": json.dumps(s.input),
            "output.value": json.dumps(s.output),
        }
        if s.is_llm:
            attrs.update({
                "llm.model_name": s.model,
                "llm.token_count.prompt": s.tokens_in,
                "llm.token_count.completion": s.tokens_out,
                "llm.token_count.total": s.tokens_in + s.tokens_out,
                "llm.cost.total": s.cost,
            })
        events = ([{"name": "exception", "attributes": {"exception.message": s.error},
                    "time_unix_nano": 0}] if s.error else None)
        spans.append(make_phoenix_span(
            s.name, golden.trace_id, f"{golden.trace_id}-{i}", parent_id=root_id,
            span_kind="LLM" if s.is_llm else "CHAIN",
            status_code="ERROR" if s.error else "OK",
            start_time=BASE + timedelta(seconds=s.start), duration_s=s.duration,
            attributes=attrs, events=events,
        ))
    return PhoenixSource(client=FakePhoenixClient([spans]))


# Adapter name (as registered in source_registry) -> golden renderer.
RENDERERS: dict[str, Callable[[GoldenTrace], Any]] = {
    "langfuse": render_langfuse,
    "phoenix": render_phoenix,
}


# ------------------------------------------------------------- comparison


def run_fingerprint(run: PipelineRun) -> dict[str, Any]:
    """The displayed facts of a run, independent of backend bookkeeping."""
    return {
        "stage": run.stage.value,
        "phase": run.phase.value,
        "doc_type": run.doc_type,
        "doc_subclass": run.doc_subclass,
        "filename": run.filename,
        "matter_id": run.matter_id,
        "session_id": run.session_id,
        "environment": run.environment,
        "tags": sorted(run.tags),
        "attempt": run.attempt,
        "classification_confidence": run.classification_confidence,
        "extraction_confidence": run.extraction_confidence,
        "escalation_reason": run.escalation_reason,
        "error_message": run.error_message,
        "run_aborted": run.run_aborted,
        "failure_class": run.failure_class,
        "routing_path": list(run.routing_path),
        # The root chain is the run itself. Langfuse also lists it as an
        # observation, Phoenix does not; it is never a floor station.
        "spans": [(s.name, s.observation_type) for s in run.spans
                  if s.name != CONTRACT["trace_name"]],
        "generations": [(g.name, g.model) for g in run.generations],
        "llm_call_count": run.llm_call_count,
        "total_tokens": run.total_tokens,
        "cost_usd": round(run.cost_usd, 9),
        "verdict": run.verdict,
        "quality": run.quality,
    }


def assert_conformant(adapter: str, render: Callable[[GoldenTrace], Any],
                      reference: Callable[[GoldenTrace], Any] = render_langfuse) -> None:
    """Every golden trace must fingerprint identically through ``adapter``."""
    for golden in GOLDEN_TRACES:
        want = run_fingerprint(reference(golden).get_run(golden.trace_id))
        run = render(golden).get_run(golden.trace_id)
        assert run is not None, f"{adapter}: {golden.trace_id} not found"
        got = run_fingerprint(run)
        diff = {k: (want[k], got[k]) for k in want if want[k] != got[k]}
        assert not diff, f"{adapter} diverges on {golden.trace_id}: {diff}"
