"""Seed demo traces INTO Langfuse (env `demo`) for UI/UX play-testing.

The Mailroom never serves canned data — demo runs are written into the real
Langfuse project configured in .env (the same project the server reads), as
full `document-pipeline` traces with verb-first node spans, LLM generations
and judge scores. They land in the `demo` environment (tags `mailroom`,
`demo`, `run-N`), separable via `MAILROOM_TRACE_ENVIRONMENTS=demo`.

Usage:
    python scripts/seed_demo.py                  # seed the full demo set
    python scripts/seed_demo.py --list-scenarios
    python scripts/seed_demo.py --scenario contract-clean
    python scripts/seed_demo.py --check          # fetch + interpret back
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from langfuse.api.ingestion.types import (
    CreateGenerationBody,
    CreateSpanBody,
    IngestionEvent_GenerationCreate,
    IngestionEvent_ScoreCreate,
    IngestionEvent_SpanCreate,
    IngestionEvent_TraceCreate,
    ScoreBody,
    TraceBody,
)

GEN_MODELS = {
    "classify": ("gpt-4o-mini", 400, 700),
    "extract": ("gpt-4o", 1800, 2600),
    "adjudicate": ("gpt-4o", 1200, 900),
    "route": ("gpt-4o", 900, 300),
    "report": ("gpt-4o-mini", 700, 1100),
    "catalog": ("gpt-4o-mini", 350, 500),
}

SPAN_MS = {
    "ingest-document": 3200,
    "classify-document": 7200,
    "extract-fields": 14000,
    "route-for-review": 4100,
    "adjudicate-conflict": 8300,
    "compile-report": 5100,
    "write-catalog": 2900,
    "archive-document": 1500,
}

MODEL_RATES = {"gpt-4o": (5.0, 15.0), "gpt-4o-mini": (0.15, 0.60)}


def gen_cost(model: str, inp: int, out: int) -> float:
    rate_in, rate_out = MODEL_RATES[model]
    return (inp * rate_in + out * rate_out) / 1_000_000


@dataclass
class DemoRun:
    tid: str
    trace: TraceBody
    spans: list[CreateSpanBody] = field(default_factory=list)
    gens: list[CreateGenerationBody] = field(default_factory=list)
    scores: list[ScoreBody] = field(default_factory=list)


def _span(tid, name, start, end, *, level="DEFAULT", output=None, input=None):
    return CreateSpanBody(
        id=f"{tid}-{name}",
        trace_id=tid,
        name=name,
        start_time=start,
        end_time=end,
        level=level,
        input=input or {},
        output=output or {"status": "ok"},
        metadata={"seed": "seed_demo"},
    )


def _gen(tid, name, start, end, *, agent, model, inp, out):
    return CreateGenerationBody(
        id=f"{tid}-{name}-gen",
        trace_id=tid,
        name=name,
        model=model,
        start_time=start,
        end_time=end,
        level="DEFAULT",
        usage={"input": inp, "output": out, "total": inp + out},
        usage_details={"input": inp, "output": out, "total": inp + out},
        cost_details={"input": 0.0, "output": 0.0, "total": gen_cost(model, inp, out)},
        metadata={"agent": agent, "seed": "seed_demo"},
        input={"prompt_sha": "demo"},
        output={"reply_sha": "demo"},
    )


JUDGE_CONFIG_NAME = "mailroom-pipeline-judge"
JUDGE_CATEGORIES = [
    {"value": 0, "label": "CORRECT"},
    {"value": 1, "label": "PARTIAL"},
    {"value": 2, "label": "MISS"},
]


def ensure_score_configs(client) -> str:
    """Ensure the CATEGORICAL judge-verdict config exists; return its id.

    Langfuse stores CATEGORICAL score values as a numeric index into a score
    config's categories, so verdicts need a real config to survive the API.
    """
    cfg_api = client.api.score_configs
    existing = {}
    try:
        for cfg in cfg_api.get().data:
            existing[cfg.name] = cfg
    except Exception:
        pass
    cfg = existing.get(JUDGE_CONFIG_NAME)
    if cfg is not None:
        return cfg.id
    created = cfg_api.create(name=JUDGE_CONFIG_NAME, data_type="CATEGORICAL",
                             categories=JUDGE_CATEGORIES)
    print(f"  created score config {JUDGE_CONFIG_NAME} ({created.id})")
    return created.id


def _score(tid, name, value, data_type="NUMERIC", comment=None, config_id=None):
    score_id = f"{tid}-{name}"
    return ScoreBody(id=score_id, name=name, value=value, trace_id=tid,
                     data_type=data_type, comment=comment, config_id=config_id)


def add_node(run, cursor, name, *, level="DEFAULT", output=None, gen=None, agent=None,
             gen_scale=0.85):
    ms = SPAN_MS[name]
    start = cursor
    end = cursor + timedelta(milliseconds=ms)
    run.spans.append(_span(run.tid, name, start, end, level=level, output=output))
    if gen and agent:
        model, inp, out = GEN_MODELS[gen]
        run.gens.append(_gen(run.tid, name, start, start + timedelta(milliseconds=ms * gen_scale),
                             agent=agent, model=model, inp=inp, out=out))
    return end


def build_run(spec, start):
    tid = f"demo-{spec['slug']}"
    t0 = start
    t1 = t0 + timedelta(seconds=1)
    doc = spec["doc_type"]
    run = DemoRun(
        tid=tid,
        trace=TraceBody(
            id=tid,
            name="document-pipeline",
            timestamp=t0,
            environment=spec.get("env", "demo"),
            tags=["mailroom", spec.get("env", "demo"), f"run-{spec['run']}", "source-seed_demo"],
            session_id=spec["matter"],
            input={
                "filename": spec["filename"],
                "matter_id": spec["matter"],
                "doc_type": doc,
                "attempt": spec.get("attempt", 1),
                "source": "demo-corpus",
            },
            output=spec["trace_output"],
            metadata={
                "attempt": spec.get("attempt", 1),
                "run_id": tid,
                "run_deadline": (t1 + timedelta(minutes=45)).isoformat(),
                "seed": "seed_demo",
            },
        ),
    )
    cursor = t1
    cursor = add_node(run, cursor, "ingest-document")
    cursor = add_node(run, cursor, "classify-document", gen="classify", agent="sorter")
    if spec.get("retry_classify"):
        cursor = add_node(run, cursor, "classify-document", gen="classify", agent="sorter")
    if spec.get("inflight"):
        run.spans.append(_span(run.tid, "extract-fields", cursor, cursor, output={"status": "running"}))
        return run
    cursor = add_node(run, cursor, "extract-fields", level=spec.get("extract_level", "DEFAULT"),
                      output=spec.get("extract_output"), gen="extract", agent=spec["specialist"])
    if spec.get("retry_extract"):
        cursor = add_node(run, cursor, "extract-fields", gen="extract", agent=spec["specialist"])
    if spec.get("failed"):
        return run
    if spec.get("review"):
        cursor = add_node(run, cursor, "route-for-review", gen="route", agent=spec["specialist"],
                          output={"decision": "review", "reason": spec.get("escalation")})
        return run
    if spec.get("boss"):
        cursor = add_node(run, cursor, "adjudicate-conflict", gen="adjudicate", agent="boss",
                          output={"decision": "override", "conflict": True})
    cursor = add_node(run, cursor, "compile-report", gen="report", agent="reporter")
    cursor = add_node(run, cursor, "write-catalog", gen="catalog", agent="archivist")
    add_node(run, cursor, "archive-document")
    for name, value in spec.get("extra_scores", {}).items():
        run.scores.append(_score(run.tid, name, value))
    return run


SPECS = [
    {"slug": "contract-clean", "run": 1,
     "filename": "contract_03_service_agreement.pdf", "doc_type": "contract",
     "matter": "demo-matter-acme-services", "specialist": "contracts_specialist",
     "verdict": "CORRECT", "quality": 0.97, "conf_cls": 0.98, "conf_ext": 0.96,
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.98, "extraction_confidence": 0.96}},
    {"slug": "contract-partial", "run": 2,
     "filename": "contract_05_master_services_agreement.pdf", "doc_type": "contract",
     "matter": "demo-matter-acme-services", "specialist": "contracts_specialist",
     "verdict": "PARTIAL", "quality": 0.58, "conf_cls": 0.97, "conf_ext": 0.63,
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.97, "extraction_confidence": 0.63,
                      "error_message": "2 fields below confidence threshold"}},
    {"slug": "corporate-ok", "run": 3,
     "filename": "corporate_04_bylaws_amendment.pdf", "doc_type": "corporate_record",
     "matter": "demo-matter-northwind", "specialist": "corporate_records_specialist",
     "verdict": "CORRECT", "quality": 0.95, "conf_cls": 0.99, "conf_ext": 0.97,
     "trace_output": {"stage": "archived", "doc_type": "corporate_record",
                      "classification_confidence": 0.99, "extraction_confidence": 0.97}},
    {"slug": "due-diligence-review", "run": 4,
     "filename": "due_diligence_07_liability_checklist.pdf", "doc_type": "due_diligence",
     "matter": "demo-matter-northwind", "specialist": "due_diligence_specialist",
     "verdict": "PARTIAL", "quality": 0.44, "conf_cls": 0.93, "conf_ext": 0.61,
     "review": True, "escalation": "low extraction confidence (0.61) on indemnification clause",
     "trace_output": {"stage": "review", "doc_type": "due_diligence",
                      "classification_confidence": 0.93, "extraction_confidence": 0.61,
                      "review_decision": "human review",
                      "escalation_reason": "low extraction confidence (0.61) on indemnification clause"}},
    {"slug": "correspondence-miss", "run": 5,
     "filename": "correspondence_09_demand_letter.pdf", "doc_type": "correspondence",
     "matter": "demo-matter-harbor", "specialist": "correspondence_specialist",
     "verdict": "MISS", "quality": 0.31, "conf_cls": 0.93, "conf_ext": 0.88,
     "trace_output": {"stage": "archived", "doc_type": "correspondence",
                      "classification_confidence": 0.93, "extraction_confidence": 0.88,
                      "error_message": "judge: deadline field missed"}},
    {"slug": "compliance-failed", "run": 6,
     "filename": "compliance_02_regulatory_filing.pdf", "doc_type": "compliance_filing",
     "matter": "demo-matter-harbor", "specialist": "compliance_specialist",
     "conf_cls": 0.91, "conf_ext": None,
     "extract_level": "ERROR", "extract_output": {"error": "extraction failed: LLM output not valid JSON"},
     "failed": True,
     "trace_output": {"stage": "failed", "doc_type": "compliance_filing",
                      "classification_confidence": 0.91,
                      "error_message": "extraction failed: LLM output not valid JSON",
                      "run_aborted": True}},
    {"slug": "court-inflight", "run": 7,
     "filename": "court_opinion_01_appeal_ruling.pdf", "doc_type": "court_opinion",
     "matter": "demo-matter-harbor", "specialist": "court_opinions_specialist",
     "conf_cls": 0.96, "conf_ext": None, "inflight": True,
     "trace_output": {"doc_type": "court_opinion",
                      "classification_confidence": 0.96}},
    {"slug": "contract-retry", "run": 8,
     "filename": "contract_06_consulting_agreement.pdf", "doc_type": "contract",
     "matter": "demo-matter-acme-services", "specialist": "contracts_specialist",
     "verdict": "CORRECT", "quality": 0.9, "conf_cls": 0.95, "conf_ext": 0.94,
     "retry_classify": True, "retry_extract": True,
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.95, "extraction_confidence": 0.94}},
    {"slug": "boss-conflict", "run": 9,
     "filename": "contract_04_joint_venture_agreement.pdf", "doc_type": "contract",
     "matter": "demo-matter-acme-services", "specialist": "contracts_specialist",
     "verdict": "PARTIAL", "quality": 0.66, "conf_cls": 0.94, "conf_ext": 0.72,
     "boss": True, "escalation": "conflicting specialist extraction on effective date",
     "extra_scores": {"conflict_detected": True, "conflict_threshold_breach": 0.41},
     "trace_output": {"stage": "archived", "doc_type": "contract",
                      "classification_confidence": 0.94, "extraction_confidence": 0.72,
                      "escalation_reason": "conflicting specialist extraction on effective date"}},
    {"slug": "low-confidence", "run": 10,
     "filename": "correspondence_04_internal_memo.pdf", "doc_type": "correspondence",
     "matter": "demo-matter-northwind", "specialist": "correspondence_specialist",
     "verdict": "PARTIAL", "quality": 0.5, "conf_cls": 0.52, "conf_ext": 0.81,
     "trace_output": {"stage": "archived", "doc_type": "correspondence",
                      "classification_confidence": 0.52, "extraction_confidence": 0.81}},
]

SCENARIO_FLAGS = {
    "due-diligence-review": ["review siding"],
    "compliance-failed": ["failed"],
    "court-inflight": ["in-flight"],
    "contract-retry": ["retry"],
    "boss-conflict": ["boss adjudication"],
    "low-confidence": ["low confidence"],
}


def _as_dict(value):
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}


def attach_scores(run, spec, judge_config_id=None):
    total_tokens = sum(_as_dict(g.usage).get("total") or 0 for g in run.gens)
    total_cost = sum(_as_dict(g.cost_details).get("total") or 0.0 for g in run.gens)
    run.scores.append(_score(run.tid, "classification_confidence", round(spec["conf_cls"], 3)))
    if spec["conf_ext"] is not None:
        run.scores.append(_score(run.tid, "extraction_confidence", round(spec["conf_ext"], 3)))
    run.scores.append(_score(run.tid, "estimated_cost_usd", round(total_cost, 5)))
    run.scores.append(_score(run.tid, "total_tokens", total_tokens))
    run.scores.append(_score(run.tid, "stage_completed", True, "BOOLEAN"))
    if spec.get("verdict"):
        run.scores.append(_score(run.tid, JUDGE_CONFIG_NAME, spec["verdict"],
                                 "CATEGORICAL", comment="demo judge run",
                                 config_id=judge_config_id))
        run.scores.append(_score(run.tid, "mailroom-pipeline-quality", spec["quality"],
                                 comment="demo judge run"))


def make_events(run):
    ts = run.trace.timestamp.isoformat()
    events = [IngestionEvent_TraceCreate(id=f"{run.tid}-trace", timestamp=ts, metadata=None,
                                         body=run.trace)]
    for i, s in enumerate(run.spans):
        events.append(IngestionEvent_SpanCreate(id=f"{run.tid}-span-{i}", timestamp=ts,
                                                metadata=None, body=s))
    for i, g in enumerate(run.gens):
        events.append(IngestionEvent_GenerationCreate(id=f"{run.tid}-gen-{i}", timestamp=ts,
                                                      metadata=None, body=g))
    for i, sc in enumerate(run.scores):
        events.append(IngestionEvent_ScoreCreate(id=sc.id, timestamp=ts, metadata=None,
                                                 body=sc))
    return events


def reset_demo_traces(client, specs, settle_s=15):
    """Delete previously seeded demo traces and wait out the delete backlog.

    Ingestion appends (re-seeding duplicates observations) and trace deletes
    are processed asynchronously, so re-seeding must start from a clean state
    or a late delete wipes the fresh traces. GET-verifying deletes is
    unusable (a GET on a deleted trace takes ~15s), so we sleep the backlog
    out instead.
    """
    trace_api = client.api.trace
    tids = [f"demo-{spec['slug']}" for spec in specs]
    for tid in tids:
        try:
            trace_api.delete(tid)
            print(f"  cleared {tid}")
        except Exception:
            pass
    time.sleep(settle_s)
    print("  deletes settled")


def make_langfuse_client():
    from langfuse import Langfuse

    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing env vars: {', '.join(missing)} (copy .env.example -> .env and fill in)")
    return Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
    )


def seed(client, specs, start_base, window, judge_config_id=None):
    batch = []
    step = window / max(1, len(specs))
    for i, spec in enumerate(specs):
        run = build_run(spec, start_base - step * i)
        attach_scores(run, spec, judge_config_id)
        batch.extend(make_events(run))
    resp = client.api.ingestion.batch(batch=batch)
    for err in (getattr(resp, "errors", None) or [])[:10]:
        print(f"  ingestion error: {err}", file=sys.stderr)
    return resp


def expected_values(spec):
    """Rebuild the exact run the seeder writes (same code path) so the
    readback can be asserted against it — verification, not fabrication."""
    expect = build_run(spec, datetime.now(timezone.utc))
    attach_scores(expect, spec)
    tokens = sum(_as_dict(g.usage).get("total") or 0 for g in expect.gens)
    cost = sum(_as_dict(g.cost_details).get("total") or 0.0 for g in expect.gens)
    if spec.get("failed"):
        stage = "failed"
    elif spec.get("review"):
        stage = "review"
    elif spec.get("inflight"):
        stage = "extract"
    else:
        stage = "archived"
    return {
        "tid": f"demo-{spec['slug']}",
        "filename": spec["filename"],
        "stage": stage,
        "doc_type": spec["doc_type"],
        "verdict": spec.get("verdict"),
        "quality": spec.get("quality"),
        "conf_cls": spec["conf_cls"],
        "conf_ext": spec["conf_ext"],
        "tokens": tokens,
        "cost": cost,
        # Langfuse v4 adds a root span named after the trace to every trace
        # that has observations — account for it in the span-count check.
        "spans": len(expect.spans) + 1,
        "gens": len(expect.gens),
    }


def _got_value(run, key):
    """Read a field off either a PipelineRun or the server's serialized dict."""
    if hasattr(run, key):
        value = getattr(run, key)
        if key == "stage":
            return value.value if hasattr(value, "value") else value
        return value
    return run.get(key) if isinstance(run, dict) else None


def assert_run(expect: dict, run, label: str) -> list[str]:
    """Assert an interpreted/displayed run against the seeded expectation.
    Returns a list of mismatch descriptions (empty == verified)."""
    fails = []
    stage = _got_value(run, "stage")
    if stage != expect["stage"]:
        fails.append(f"stage {stage!r} != {expect['stage']!r}")
    doc_type = _got_value(run, "doc_type")
    if doc_type != expect["doc_type"]:
        fails.append(f"doc_type {doc_type!r} != {expect['doc_type']!r}")
    verdict = _got_value(run, "verdict")
    if verdict != expect["verdict"]:
        fails.append(f"verdict {verdict!r} != {expect['verdict']!r}")
    quality = _got_value(run, "quality")
    if expect["quality"] is not None and (quality is None or abs(float(quality) - expect["quality"]) > 0.02):
        fails.append(f"quality {quality!r} != {expect['quality']}")
    conf_cls = _got_value(run, "classification_confidence")
    if conf_cls is None or abs(float(conf_cls) - expect["conf_cls"]) > 0.01:
        fails.append(f"classification_confidence {conf_cls!r} != {expect['conf_cls']}")
    conf_ext = _got_value(run, "extraction_confidence")
    if expect["conf_ext"] is None:
        if conf_ext is not None:
            fails.append(f"extraction_confidence {conf_ext!r} != None")
    elif conf_ext is None or abs(float(conf_ext) - expect["conf_ext"]) > 0.01:
        fails.append(f"extraction_confidence {conf_ext!r} != {expect['conf_ext']}")
    tokens = _got_value(run, "total_tokens")
    if tokens != expect["tokens"]:
        fails.append(f"total_tokens {tokens} != {expect['tokens']}")
    cost = _got_value(run, "cost_usd")
    if cost is None or abs(float(cost) - expect["cost"]) > 0.001:
        fails.append(f"cost_usd {cost!r} != {expect['cost']}")
    spans = _got_value(run, "spans")
    if isinstance(spans, list) and len(spans) not in (expect["spans"], expect["spans"] - 1):
        fails.append(f"span count {len(spans)} != {expect['spans']}")
    gens = _got_value(run, "generations")
    if isinstance(gens, list) and len(gens) != expect["gens"]:
        fails.append(f"generation count {len(gens)} != {expect['gens']}")
    if fails:
        print(f"  FAIL {label} ({expect['tid']}): " + "; ".join(fails))
    else:
        print(f"  PASS {label} ({expect['tid']}) stage={expect['stage']} "
              f"verdict={expect['verdict'] or '-'} tokens={expect['tokens']} cost=${expect['cost']:.4f}")
    return fails


def run_check(specs, check_api: bool, api_base: str) -> None:
    from mailroom_ui.langfuse_source import LangfuseSource

    src = LangfuseSource()
    expects = [expected_values(s) for s in specs]
    tids = [e["tid"] for e in expects]
    print(f"\nVERIFY against stored Langfuse logs ({len(tids)} runs)...")
    fails = 0
    found = 0
    for expect in expects:
        run = src.get_run(expect["tid"])
        if run is None:
            print(f"  FAIL stored (missing trace {expect['tid']})")
            fails += 1
            continue
        found += 1
        fails += len(assert_run(expect, run, "stored"))

    if check_api:
        import urllib.request

        print(f"\nVERIFY against live server display API ({api_base})...")
        for expect in expects:
            try:
                with urllib.request.urlopen(f"{api_base}/api/traces/{expect['tid']}",
                                            timeout=20) as resp:
                    payload = json.loads(resp.read().decode())
            except Exception as err:
                print(f"  FAIL api (unreachable: {err})")
                fails += 1
                continue
            if payload.get("error"):
                print(f"  FAIL api ({payload['error']})")
                fails += 1
                continue
            fails += len(assert_run(expect, payload, "api"))

    print(f"\n{found}/{len(tids)} traces present in the stored logs; "
          f"{'ALL CHECKS PASSED' if fails == 0 else f'{fails} MISMATCH(ES)'}")
    return fails


def main():
    parser = argparse.ArgumentParser(description="Seed demo traces into Langfuse (env demo).")
    parser.add_argument("--list-scenarios", action="store_true", help="list available demo scenarios")
    parser.add_argument("--scenario", help="seed a single scenario by slug")
    parser.add_argument("--count", type=int, default=len(SPECS), help="number of demo runs to seed")
    parser.add_argument("--env", default="demo", help="environment tag (default: demo)")
    parser.add_argument("--window-hours", type=float, default=3.0,
                        help="spread runs across this many hours back from now")
    parser.add_argument("--check", action="store_true",
                        help="verify seeded traces against the stored Langfuse logs")
    parser.add_argument("--check-api", action="store_true",
                        help="also verify against a running server's display API "
                             "(implies --check)")
    parser.add_argument("--api-base", default="http://127.0.0.1:8001",
                        help="base URL of the running The-Mailroom server")
    parser.add_argument("--keep", action="store_true",
                        help="do not delete previously seeded demo traces first")
    args = parser.parse_args()

    load_dotenv()

    if args.list_scenarios:
        for spec in SPECS:
            flags = ", ".join(SCENARIO_FLAGS.get(spec["slug"], [])) or "-"
            stage = spec["trace_output"]["stage"]
            print(f"{spec['slug']:24} {spec['filename']:48} {stage:10} {flags}")
        return

    specs = [dict(s) for s in SPECS]
    if args.scenario:
        specs = [s for s in specs if s["slug"] == args.scenario]
        if not specs:
            sys.exit(f"unknown scenario '{args.scenario}' (see --list-scenarios)")
    specs = specs[: args.count]
    for i, spec in enumerate(specs):
        spec["env"] = args.env
        spec["run"] = i + 1

    client = make_langfuse_client()
    judge_config_id = ensure_score_configs(client)
    if not args.keep:
        reset_demo_traces(client, specs)
    start_base = datetime.now(timezone.utc) - timedelta(minutes=1)
    print(f"seeding {len(specs)} demo run(s) into Langfuse (env={args.env}) ...")
    resp = seed(client, specs, start_base, timedelta(hours=args.window_hours),
                judge_config_id)
    success = len(getattr(resp, "successes", None) or [])
    errors = len(getattr(resp, "errors", None) or [])
    print(f"ingestion accepted: {success} event(s), {errors} error(s)")
    for spec in specs:
        tid = f"demo-{spec['slug']}"
        host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com").rstrip("/")
        print(f"  {spec['slug']:24} {host}/trace/{tid}")
    client.shutdown()

    if args.check or args.check_api:
        time.sleep(15)
        sys.exit(0 if run_check(specs, args.check_api, args.api_base) == 0 else 1)


if __name__ == "__main__":
    main()
