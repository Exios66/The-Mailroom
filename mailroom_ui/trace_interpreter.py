"""Trace interpreter: Langfuse trace + observations + scores -> PipelineRun.

The mapping mirrors llm-mailroom's graph topology (see pipeline_schema.py).
The trace structure is: one `document-pipeline` trace per document, verb-first
node spans (`classify-document`, `extract-fields`, ...), auto-traced LLM
generations, and scores (confidences, run metrics, judge verdicts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .models import Generation, NodeSpan, PipelineRun, Score, Stage
from .pipeline_schema import (
    NODE_ORDER,
    SPAN_STAGE_MAP,
    STAGE_PHASE,
    PipelineSchema,
)

# Score names produced by observability/scores.py + Langfuse evaluators.
JUDGE_VERDICT_SCORES = ("mailroom-pipeline-judge",)
JUDGE_QUALITY_SCORES = ("mailroom-pipeline-quality",)

_OUTPUT_STAGE_MAP = {
    "archived": Stage.ARCHIVED,
    "failed": Stage.FAILED,
    "review": Stage.HUMAN_REVIEW,
    "processing": Stage.INGEST,
    "classified": Stage.CLASSIFY,
    "extracting": Stage.EXTRACT,
    "reporting": Stage.COMPILE_REPORT,
    "inbox": Stage.INBOX,
}

_LIVE_STAGE_NAMES = {s.value for s in Stage}

DEFAULT_SCHEMA = PipelineSchema.load()


def parse_dt(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def _pick(d: dict[str, Any], *keys: str) -> Any:
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:
            return value.model_dump()
    return value if isinstance(value, dict) else {}


def _usage_tokens(usage: Any) -> tuple[Optional[int], Optional[int], Optional[int]]:
    usage = _as_dict(usage)
    return (
        usage.get("total") or usage.get("total_tokens"),
        usage.get("input") or usage.get("prompt_tokens"),
        usage.get("output") or usage.get("completion_tokens"),
    )


def _cost_details(cost: Any) -> float:
    cost = _as_dict(cost)
    total = cost.get("total") or cost.get("total_cost")
    if total is not None:
        return float(total)
    inp = cost.get("input") or cost.get("input_cost") or 0
    out = cost.get("output") or cost.get("output_cost") or 0
    return float(inp) + float(out)


def derive_stage(
    output: dict[str, Any],
    spans: list[NodeSpan],
    *,
    schema: PipelineSchema = DEFAULT_SCHEMA,
) -> Stage:
    """Primary: trace output `stage`; fallback: last node span; else INBOX."""
    raw = _clean(output.get("stage"))
    if raw:
        mapped = _OUTPUT_STAGE_MAP.get(raw.lower(), None)
        if mapped is not None:
            return mapped
        if raw.lower() in _LIVE_STAGE_NAMES:
            return Stage(raw.lower())
    for span in reversed(spans):
        if span.name in SPAN_STAGE_MAP:
            return SPAN_STAGE_MAP[span.name]
    return Stage.INBOX


def build_routing_path(spans: list[NodeSpan]) -> list[str]:
    """Stable node sequence incl. retries (consecutive repeats)."""
    staged: list[Stage] = []
    prev: Optional[Stage] = None
    for span in spans:
        stage = SPAN_STAGE_MAP.get(span.name)
        if stage is None:
            continue
        if prev is not None and stage == prev:
            if stage == Stage.CLASSIFY:
                staged.append(Stage.RETRY_CLASSIFY)
            elif stage == Stage.EXTRACT:
                staged.append(Stage.RETRY_EXTRACT)
            continue
        staged.append(stage)
        prev = stage
    staged.sort(key=lambda s: NODE_ORDER.index(s) if s in NODE_ORDER else 99)
    return [s.value for s in staged]


def _observation_name(obs: dict[str, Any]) -> Optional[str]:
    name = _clean(obs.get("name"))
    if name:
        return name
    return _clean(obs.get("type"))


# Pilot/attempt re-runs reuse the deterministic trace id, so a trace can carry
# several full runs of the same document. Observations are clustered by time
# gaps (> RUN_GAP_S between consecutive observations starts a new cluster) and
# only the latest cluster is displayed — one envelope per trace, latest run.
RUN_GAP_S = 60.0


def _latest_cluster(items: list[Any], *, get_start) -> list[Any]:
    """Keep only the trailing cluster of a chronological sequence."""
    if len(items) < 2:
        return items
    ordered = sorted(items, key=lambda i: get_start(i) or datetime.min)
    start_times = [get_start(i) for i in ordered]
    gap_at: Optional[int] = None
    prev: Optional[datetime] = None
    for idx, t in enumerate(start_times):
        if t is not None and prev is not None:
            try:
                if (t - prev).total_seconds() > RUN_GAP_S:
                    gap_at = idx
            except TypeError:
                pass
        if t is not None:
            prev = t
    if gap_at is None:
        return items
    return ordered[gap_at:]


def interpret_trace(
    trace: dict[str, Any],
    observations: Optional[list[dict[str, Any]]] = None,
    scores: Optional[list[dict[str, Any]]] = None,
    *,
    schema: PipelineSchema = DEFAULT_SCHEMA,
) -> PipelineRun:
    """Interpret one Langfuse trace into a display-ready PipelineRun.

    `observations`/`scores` are optional: when omitted the run is a "light"
    interpretation (list-level data only) with no span/generation detail.
    """
    trace = _as_dict(trace)
    observations = observations or []
    scores = scores or []
    embedded_obs = trace.get("observations")
    if not observations and isinstance(embedded_obs, list):
        observations = [_as_dict(o) for o in embedded_obs]
    embedded_scores = trace.get("scores")
    if not scores and isinstance(embedded_scores, list):
        scores = [_as_dict(s) for s in embedded_scores]
    t_input = _as_dict(trace.get("input"))
    t_output = _as_dict(trace.get("output"))
    metadata = _as_dict(trace.get("metadata"))
    tags = [str(t) for t in (trace.get("tags") or []) if t]
    environment = _clean(trace.get("environment"))

    created = parse_dt(_pick(trace, "timestamp", "created_at"))
    latency = trace.get("latency")
    if latency is not None:
        try:
            latency = float(latency)
        except (TypeError, ValueError):
            latency = None

    spans: list[NodeSpan] = []
    generations: list[Generation] = []
    for raw in observations:
        obs = _as_dict(raw)
        obs_type = str(obs.get("type") or "").upper()
        start = parse_dt(obs.get("start_time"))
        end = parse_dt(obs.get("end_time"))
        obs_latency = obs.get("latency")
        try:
            obs_latency = float(obs_latency) if obs_latency is not None else None
        except (TypeError, ValueError):
            obs_latency = None
        is_error = str(obs.get("level") or "").upper() in ("ERROR", "WARNING") or bool(
            obs.get("error") or _as_dict(obs.get("output")).get("error")
        )
        if obs_type in ("SPAN", "EVENT", "OBSERVATION"):
            if "model" in obs or obs_type == "GENERATION":
                pass  # fall through to generation classification below
        if obs_type == "GENERATION" or obs.get("model") is not None or "usage" in obs:
            name = _observation_name(obs)
            usage_in, usage_out = _usage_tokens(obs.get("usage"))[1:]
            total = _usage_tokens(obs.get("usage"))[0]
            generations.append(
                Generation(
                    name=name,
                    agent=_clean(obs.get("metadata", {}).get("agent"))
                    if isinstance(obs.get("metadata"), dict)
                    else None,
                    model=_clean(obs.get("model")),
                    latency=obs_latency,
                    input=obs.get("input"),
                    output=obs.get("output"),
                    usage_total_tokens=total,
                    usage_input_tokens=usage_in,
                    usage_output_tokens=usage_out,
                    cost_usd=_cost_details(obs.get("cost_details")) or None,
                    prompt_version=_clean(
                        _pick(
                            _as_dict(obs.get("metadata")),
                            "langfuse_prompt",
                            "prompt_id",
                            "prompt_version",
                        )
                    ),
                    start_time=start,
                    end_time=end,
                )
            )
        elif obs_type in ("SPAN", "EVENT", "OBSERVATION"):
            spans.append(
                NodeSpan(
                    name=_observation_name(obs) or "observation",
                    start_time=start,
                    end_time=end,
                    latency=obs_latency,
                    status="ERROR" if is_error else "SUCCESS",
                    error_message=_clean(
                        obs.get("error")
                        or _as_dict(obs.get("output")).get("error")
                        or obs.get("metadata", {}).get("error")
                        if isinstance(obs.get("metadata"), dict)
                        else obs.get("error")
                    ),
                    input=_as_dict(obs.get("input")) or None,
                    output=_as_dict(obs.get("output")) or None,
                )
            )

    spans.sort(key=lambda s: s.start_time or datetime.min)
    generations.sort(key=lambda g: g.start_time or datetime.min)
    # A trace may carry several runs (deterministic trace ids are reused by
    # pilot/attempt re-runs). Keep only the latest run's observations.
    spans = _latest_cluster(spans, get_start=lambda s: s.start_time)
    generations = _latest_cluster(generations, get_start=lambda g: g.start_time)

    score_map: dict[str, Any] = {}
    score_objects: list[Score] = []
    for raw in scores:
        s = _as_dict(raw)
        name = _clean(s.get("name"))
        if not name:
            continue
        score_objects.append(
            Score(
                name=name,
                value=s.get("value"),
                data_type=_clean(s.get("data_type")),
                comment=_clean(s.get("comment")),
                observation_id=_clean(s.get("observation_id")),
            )
        )
        score_map[name] = s.get("value")

    stage = derive_stage(t_output, spans, schema=schema)
    routing_path = build_routing_path(spans)

    doc_type = _clean(t_output.get("doc_type")) or _clean(t_input.get("doc_type"))
    attempt = _pick(t_input, "attempt", "run_attempt")
    if attempt is None:
        attempt = metadata.get("attempt")
    filename = _clean(t_input.get("filename")) or _clean(t_input.get("file"))
    matter_id = _clean(t_input.get("matter_id"))
    session_id = _clean(trace.get("session_id"))
    if matter_id is None:
        matter_id = session_id

    verdict: Optional[str] = None
    quality: Optional[float] = None
    for name in JUDGE_VERDICT_SCORES:
        v = score_map.get(name)
        if v is not None:
            verdict = _clean(v)
            break
    for name in JUDGE_QUALITY_SCORES:
        v = score_map.get(name)
        if v is not None:
            try:
                quality = float(v)
            except (TypeError, ValueError):
                quality = None
            break

    total_tokens = sum(g.usage_total_tokens or 0 for g in generations)
    cost = sum(g.cost_usd or 0 for g in generations)

    run = PipelineRun(
        trace_id=str(trace.get("id") or ""),
        name=_clean(trace.get("name")) or "document-pipeline",
        filename=filename,
        matter_id=matter_id,
        session_id=session_id,
        environment=environment,
        tags=tags,
        attempt=int(attempt) if attempt is not None else None,
        created_at=created,
        updated_at=parse_dt(trace.get("updated_at")) or created,
        latency=latency,
        stage=stage,
        phase=STAGE_PHASE.get(stage, STAGE_PHASE[Stage.UNKNOWN]),
        doc_type=doc_type,
        classification_confidence=_float(score_map.get("classification_confidence"))
        or _float(t_output.get("classification_confidence")),
        extraction_confidence=_float(score_map.get("extraction_confidence"))
        or _float(t_output.get("extraction_confidence")),
        review_decision=_clean(t_output.get("review_decision")),
        escalation_reason=_clean(t_output.get("escalation_reason")),
        error_message=_clean(t_output.get("error_message")),
        run_aborted=bool(t_output.get("run_aborted") or score_map.get("run_aborted")),
        spans=spans,
        generations=generations,
        scores=score_map,
        routing_path=routing_path,
        verdict=verdict,
        quality=quality,
        llm_call_count=len(generations),
        total_tokens=total_tokens,
        cost_usd=cost,
    )
    return run


def _float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
