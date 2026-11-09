"""Pipeline topology and taxonomy for interpreting llm-mailroom traces.

Facts about the pipeline (graph nodes and their spans, observation types,
agents, document classes with fields and subclasses, failure classes, score
aliases, confidence thresholds) come from the generated display contract the
pipeline publishes (ADR-001), vendored at ``mailroom_ui/contract/`` by
``scripts/bump_producer_pin.py``. This module keeps only what is the
visualizer's own business: which floor ``Stage`` a span lands on, phases,
display labels and roles.

If ``MAILROOM_TAXONOMY`` points at a live taxonomy.yaml, thresholds and class
labels are read from there instead.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .models import Phase, Stage

_log = logging.getLogger(__name__)

CONTRACT_PATH = Path(__file__).resolve().parent / "contract" / "mailroom-contract.json"
SUPPORTED_CONTRACT_MAJOR = 1


def load_contract(path: Path | str | None = None) -> dict[str, Any]:
    """Read the vendored pipeline display contract (fails loudly if absent)."""
    target = Path(path or os.environ.get("MAILROOM_CONTRACT") or CONTRACT_PATH)
    contract = json.loads(target.read_text(encoding="utf-8"))
    major = int(str(contract.get("contract_version", "0")).split(".")[0])
    if major != SUPPORTED_CONTRACT_MAJOR:
        raise RuntimeError(
            f"pipeline contract {target} is version {contract.get('contract_version')}; "
            f"this visualizer reads major {SUPPORTED_CONTRACT_MAJOR}"
        )
    return contract


CONTRACT: dict[str, Any] = load_contract()
CONTRACT_NODES: dict[str, dict[str, str]] = {
    node["id"]: node for node in CONTRACT["graph"]["nodes"]
}
CONTRACT_SPAN_TYPES: dict[str, str] = dict(CONTRACT["spans"])


def _graph_edges(contract: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    graph = contract.get("graph") or {}
    return tuple(
        (str(edge.get("source")), str(edge.get("target")))
        for edge in graph.get("edges") or ()
        if edge.get("source") and edge.get("target")
    )


def _edge_labels(contract: dict[str, Any]) -> dict[tuple[str, str], str]:
    """Conditional-edge label by (source, target) — ``failed`` on review→end."""
    graph = contract.get("graph") or {}
    return {
        (str(edge.get("source")), str(edge.get("target"))): str(edge["label"])
        for edge in graph.get("edges") or ()
        if edge.get("source") and edge.get("target") and edge.get("label")
    }


# Compiled graph wiring (ADR-001 contract). The floor keeps its own station
# order; the edges are what tell us a run may enter or leave a station in a
# shape the station order cannot guess (a human-resolved approval starts its
# resumed run at the reporting tail, not at intake).
GRAPH_START: str = str((CONTRACT.get("graph") or {}).get("start") or "__start__")
GRAPH_END: str = str((CONTRACT.get("graph") or {}).get("end") or "__end__")
GRAPH_EDGES: tuple[tuple[str, str], ...] = _graph_edges(CONTRACT)
GRAPH_EDGE_LABELS: dict[tuple[str, str], str] = _edge_labels(CONTRACT)

# Stations a run can legitimately START on. ``__start__`` goes to intake
# normally, to extraction when a review resume re-extracts under the manifest
# class, and to the reporting tail when a reviewer's own fields are applied on
# a process that lost its interrupt checkpoint (llm-mailroom PR #203).
RESUME_ENTRY_STAGES: frozenset[Stage] = frozenset({Stage.EXTRACT, Stage.COMPILE_REPORT})

# Verb-first observation names (traced_node) plus LangGraph node names, so
# a floor envelope never falls through to INBOX/unknown when the producer
# records the underscored graph id instead of the display span.
SPAN_STAGE_MAP: dict[str, Stage] = {
    "intake-document": Stage.INTAKE,
    "normalize-intake": Stage.INTAKE,
    # ModernBERT fast-path triage (llm-mailroom #85 M6a) — a SPAN inside
    # intake_node, always emitted (fail-open: available=false when off).
    "intake-ml-triage": Stage.INTAKE,
    "transcribe-pdf": Stage.INTAKE,
    "extract-image-text": Stage.INTAKE,
    "classify-document": Stage.CLASSIFY,
    "judge-verify": Stage.JUDGE_VERIFY,
    "arbitrate-verdict": Stage.ARBITER,
    # Classification arbiter (sorter vs reviewer disagreement). Interim: it
    # shares the re-classify station until A-4 gives it its own stage.
    "arbitrate-classification": Stage.RETRY_CLASSIFY,
    "extract-fields": Stage.EXTRACT,
    "route-for-review": Stage.HUMAN_REVIEW,
    "adjudicate-conflict": Stage.BOSS,
    "compile-report": Stage.COMPILE_REPORT,
    "write-catalog": Stage.CATALOG,
    "archive-document": Stage.ARCHIVE,
    # LangGraph add_node ids (build_graph.py)
    "intake": Stage.INTAKE,
    "classify": Stage.CLASSIFY,
    "retry_classify": Stage.RETRY_CLASSIFY,
    "review_classify": Stage.RETRY_CLASSIFY,
    "classification_arbiter": Stage.RETRY_CLASSIFY,
    "extract": Stage.EXTRACT,
    "retry_extract": Stage.RETRY_EXTRACT,
    "judge_verify": Stage.JUDGE_VERIFY,
    "arbiter": Stage.ARBITER,
    "human_review": Stage.HUMAN_REVIEW,
    "boss_escalation": Stage.BOSS,
    "compile_report": Stage.COMPILE_REPORT,
    "catalog_write": Stage.CATALOG,
    "archive": Stage.ARCHIVE,
}

# mailroom-reloaded (CrewAI-Flows pipeline) node spans: ``mailroom.node.<node>``
# under a ``mailroom.document`` root, read through the Phoenix source. Its
# retry loops (sort -> gate -> sort) surface as consecutive repeats, which
# build_routing_path already folds into the retry stages. ``grade`` is
# eval-only and the gates are span events, so neither maps to a station.
RELOADED_NODE_PREFIX = "mailroom.node."
RELOADED_ROOT_SPAN = "mailroom.document"
RELOADED_NODE_STAGES: dict[str, Stage] = {
    "ingest": Stage.INTAKE,
    "bert_primary": Stage.INTAKE,
    "sort": Stage.CLASSIFY,
    "extract": Stage.EXTRACT,
    "verify": Stage.JUDGE_VERIFY,  # judge, then arbiter, inside one node
    "boss": Stage.BOSS,
    "human_review": Stage.HUMAN_REVIEW,
    "report_catalog_archive": Stage.ARCHIVE,
}
# Document ``mailroom.status`` -> trace output ``stage`` token.
RELOADED_STATUS_STAGES: dict[str, str] = {
    "processing": "processing",
    "archived": "archived",
    "failed": "failed",
    "parked": "review",
}
SPAN_STAGE_MAP.update(
    {f"{RELOADED_NODE_PREFIX}{k}": v for k, v in RELOADED_NODE_STAGES.items()}
)

# Contract spans that are not floor stations: the per-document root, the
# LLM result generation and LegalBench answers.
NON_STATION_SPANS: frozenset[str] = frozenset(
    {CONTRACT["trace_name"], "pipeline-result", "answer-question"}
)

# Most specific Langfuse observation type per span (chain = one document run;
# agent = specialist orchestration; evaluator = judge gate; retriever =
# document reads; generation = LLM result; span = other units of work).
# Pipeline spans come from the contract; reloaded spans are local.
NODE_OBSERVATION_TYPES: dict[str, str] = {
    **CONTRACT_SPAN_TYPES,
    RELOADED_ROOT_SPAN: "chain",
    f"{RELOADED_NODE_PREFIX}ingest": "span",
    f"{RELOADED_NODE_PREFIX}bert_primary": "span",
    f"{RELOADED_NODE_PREFIX}sort": "agent",
    f"{RELOADED_NODE_PREFIX}extract": "agent",
    f"{RELOADED_NODE_PREFIX}verify": "evaluator",
    f"{RELOADED_NODE_PREFIX}boss": "agent",
    f"{RELOADED_NODE_PREFIX}human_review": "span",
    f"{RELOADED_NODE_PREFIX}report_catalog_archive": "span",
}

# Graph node ids (underscored) that appear as observation names when a trace
# is recorded from LangGraph rather than traced_node(): same type as the
# node's span. Procedural nodes keep the generic default.
_NODE_TYPE_ALIASES: dict[str, str] = {
    node_id: node["observation_type"]
    for node_id, node in CONTRACT_NODES.items()
    if node.get("observation_type") in {"agent", "evaluator"}
}


def observation_type_for(name: str, default: str = "span") -> str:
    """Most-specific Langfuse observation type for a verb-first span name."""
    key = (name or "").strip()
    if key in NODE_OBSERVATION_TYPES:
        return NODE_OBSERVATION_TYPES[key]
    lower = key.lower()
    if lower in NODE_OBSERVATION_TYPES:
        return NODE_OBSERVATION_TYPES[lower]
    if lower in _NODE_TYPE_ALIASES:
        return _NODE_TYPE_ALIASES[lower]
    if lower.startswith("answer-question"):
        return "generation"
    return default

STAGE_PHASE: dict[Stage, Phase] = {
    Stage.INBOX: Phase.INTAKE_SORT,
    Stage.INTAKE: Phase.INTAKE_SORT,
    Stage.CLASSIFY: Phase.INTAKE_SORT,
    Stage.RETRY_CLASSIFY: Phase.INTAKE_SORT,
    Stage.EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.RETRY_EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.JUDGE_VERIFY: Phase.EXTRACTION_ADJUDICATION,
    Stage.ARBITER: Phase.EXTRACTION_ADJUDICATION,
    Stage.BOSS: Phase.EXTRACTION_ADJUDICATION,
    Stage.COMPILE_REPORT: Phase.REPORTING_ARCHIVE,
    Stage.CATALOG: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVE: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVED: Phase.TERMINAL,
    Stage.FAILED: Phase.TERMINAL,
    Stage.HUMAN_REVIEW: Phase.REVIEW,
    Stage.UNKNOWN: Phase.INTAKE_SORT,
}

# Node traversal order used to order spans into a routing path (mirrors the
# add_node wiring order in llm-mailroom graph/build_graph.py).
NODE_ORDER: list[Stage] = [
    Stage.INTAKE,
    Stage.CLASSIFY,
    Stage.RETRY_CLASSIFY,
    Stage.EXTRACT,
    Stage.RETRY_EXTRACT,
    Stage.JUDGE_VERIFY,
    Stage.ARBITER,
    Stage.BOSS,
    Stage.HUMAN_REVIEW,
    Stage.COMPILE_REPORT,
    Stage.CATALOG,
    Stage.ARCHIVE,
]

# Agent display roster: key -> (label, role). Keys come from the contract;
# labels and roles are local display metadata (unknown agents get a title-
# cased label so a new pipeline agent still renders).
_AGENT_DISPLAY: dict[str, dict[str, str]] = {
    "sorter": {"label": "Sorter", "role": "classify"},
    "intake": {"label": "Intake", "role": "prepare"},
    "sorter_reviewer": {"label": "Sorter Reviewer", "role": "review-classify"},
    "contracts_specialist": {"label": "Contracts", "role": "extract"},
    "merger_agreement_specialist": {"label": "Merger Agreements", "role": "extract"},
    "corporate_records_specialist": {"label": "Corporate", "role": "extract"},
    "correspondence_specialist": {"label": "Correspondence", "role": "extract"},
    "insurance_claims_specialist": {"label": "Insurance Claims", "role": "extract"},
    "arbiter": {"label": "Arbiter", "role": "adjudicate"},
    "boss": {"label": "Boss", "role": "adjudicate"},
    # compile_report is procedural in llm-mailroom (no get_llm).
    "reporter": {"label": "Reporter", "role": "report"},
    "judge": {"label": "Judge", "role": "evaluate"},
    "pdf_transcriber": {"label": "Transcriber", "role": "intake"},
    "image_extractor": {"label": "Image Extractor", "role": "intake"},
    "gmail_triage": {"label": "Mail Triage", "role": "triage"},
    "relations": {"label": "Relations", "role": "relate"},
}
AGENTS: dict[str, dict[str, str]] = {
    key: dict(_AGENT_DISPLAY.get(key) or {"label": key.replace("_", " ").title(), "role": "agent"})
    for key in CONTRACT["agents"]
}

# Live taxonomy classes, each with its own specialist (contract doc_classes).
# ``unknown`` is a routing token. Retired classes stay off the roster; the
# sorter emits ``unknown`` for them.
_CONTRACT_CLASSES: list[dict[str, Any]] = list(CONTRACT["doc_classes"])
LIVE_DOC_TYPES: tuple[str, ...] = tuple(dc["key"] for dc in _CONTRACT_CLASSES)
RETIRED_DOC_TYPES: tuple[str, ...] = ("court_opinion", "due_diligence", "compliance_filing")
UNKNOWN_DOC_TYPE: str = CONTRACT.get("unknown_doc_class") or "unknown"
# Sorter / HF labels that extract through a live specialist without their own
# class row. Empty: MAUD is a live class.
EXTRACT_CLASS_ALIASES: dict[str, str] = {}

DOC_CLASSES: dict[str, str] = {
    **{dc["key"]: dc["label"] for dc in _CONTRACT_CLASSES},
    UNKNOWN_DOC_TYPE: "Unknown",
}

DEFAULT_DOC_CLASSES: dict[str, str] = dict(DOC_CLASSES)

# pipeline.failures classes, stamped on aborted state / manifest / audit.
# Trace output may carry the token, or embed it as ``run aborted [x]: ...``.
FAILURE_CLASSES: tuple[str, ...] = tuple(CONTRACT["failure_classes"])
FAILURE_CLASS_LABELS: dict[str, str] = {
    "llm_timeout": "LLM timeout",
    "llm_auth": "LLM auth",
    "llm_rate_limit": "LLM rate limit",
    "llm_transient": "LLM transient",
    "io_error": "I/O error",
    "schema_error": "schema error",
    "run_budget": "run budget",
    "unexpected": "unexpected",
}
# Hand-written labels; a contract class without one still renders (derived
# label below) but shows up in contract_gaps() until someone names it.
_FAILURE_LABELS_LOCAL: frozenset[str] = frozenset(FAILURE_CLASS_LABELS)
for _fc in FAILURE_CLASSES:
    FAILURE_CLASS_LABELS.setdefault(_fc, _fc.replace("_", " "))

# Extraction schema field names per class (contract doc_classes[].fields).
# REVIEW Complete rejects keys that belong to another specialist.
_META_EXTRACT_KEYS = frozenset({"confidence", "reasoning", "mock_extraction"})
EXTRACTION_FIELD_KEYS_BY_CLASS: dict[str, frozenset[str]] = {
    dc["key"]: frozenset(dc["fields"]) for dc in _CONTRACT_CLASSES
}

_ABORT_CLASS_RE = re.compile(r"run aborted \[([a-z_]+)\]", re.I)


def all_specialist_field_keys() -> frozenset[str]:
    names: set[str] = set()
    for keys in EXTRACTION_FIELD_KEYS_BY_CLASS.values():
        names.update(keys)
    return frozenset(names) - _META_EXTRACT_KEYS


def normalize_failure_class(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip().lower().replace("-", "_")
    return key if key in FAILURE_CLASSES else None


def failure_class_from_text(text: Optional[str]) -> Optional[str]:
    """Parse ``run aborted [llm_timeout]: …`` from error / escalation text."""
    if not text:
        return None
    match = _ABORT_CLASS_RE.search(str(text))
    if not match:
        return None
    return normalize_failure_class(match.group(1))


def validate_operator_extraction(doc_type: str, extracted: dict) -> dict:
    """Reject Complete payloads whose keys belong to another specialist.

    Mirrors llm-mailroom ``pipeline.review_resolve.validate_operator_extraction``
    foreign-key check (PR #53). Full pydantic schema_valid stays on the
    producer when the live extra is present.
    """
    payload = dict(extracted)
    kind = EXTRACT_CLASS_ALIASES.get(doc_type, doc_type)
    allowed = (
        EXTRACTION_FIELD_KEYS_BY_CLASS.get(doc_type)
        or EXTRACTION_FIELD_KEYS_BY_CLASS.get(kind)
        or frozenset()
    ) | _META_EXTRACT_KEYS
    foreign = sorted(
        key
        for key in payload
        if key not in allowed
        and not str(key).startswith("_")
        and key in all_specialist_field_keys()
    )
    if foreign:
        raise ValueError(
            f"extracted_data fields {foreign} belong to another specialist, "
            f"not {doc_type}"
        )
    return payload


SPECIALIST_BY_DOC_CLASS: dict[str, str] = {
    dc["key"]: dc["specialist"] for dc in _CONTRACT_CLASSES if dc.get("specialist")
}

# Subclass catalogs per class (contract doc_classes[].subclasses: Hub
# inventories, CUAD contract subtypes, MAUD consideration types).
DOC_SUBCLASS_BY_CLASS: dict[str, tuple[str, ...]] = {
    dc["key"]: tuple(dc.get("subclasses") or ()) for dc in _CONTRACT_CLASSES
}
CONTRACT_SUBTYPE_KEYS: tuple[str, ...] = DOC_SUBCLASS_BY_CLASS.get("contract", ())

# Langfuse Cloud rejects score *config* names over 35 characters.
LANGFUSE_SCORE_NAME_ALIASES: dict[str, str] = dict(CONTRACT["scores"]["langfuse_aliases"])
# Every score config the pipeline registers (name -> data type).
SCORE_CONFIGS: dict[str, str] = {
    cfg["name"]: cfg.get("data_type", "NUMERIC") for cfg in CONTRACT["scores"]["configs"]
}
_CANONICAL_SCORE_NAMES: dict[str, str] = {
    alias: canonical for canonical, alias in LANGFUSE_SCORE_NAME_ALIASES.items()
}

# Dedicated specialist-suite extras (llm-mailroom suite_scoring.py;
# names unchanged through llm-dojo-scoring v0.16.0).
SUITE_EXTRA_SCORES: tuple[str, ...] = (
    "content_topic_accuracy",
    "content_topic_f1_macro",
    "sentiment_accuracy",
    "sentiment_f1_macro",
    "maud_question_accuracy",
    "maud_question_macro_accuracy",
    "maud_clause_presence",
    "maud_valid_class_rate",
    "maud_category_accuracy",
)
SUITE_EXTRA_SCORE_SET = frozenset(SUITE_EXTRA_SCORES)

GROUND_TRUTH_KEYS: tuple[str, ...] = (
    "expected_hf_class",
    "expected_doc_class",
    "expected_subclass",
    "expected",
)


def resolve_extract_class(doc_type: Optional[str]) -> Optional[str]:
    """Live taxonomy class used for extraction, or None if parked."""
    if not doc_type:
        return None
    key = str(doc_type).strip().lower()
    if key == UNKNOWN_DOC_TYPE or key in RETIRED_DOC_TYPES:
        return None
    aliased = EXTRACT_CLASS_ALIASES.get(key, key)
    if aliased in LIVE_DOC_TYPES:
        return aliased
    return None


def langfuse_score_name(name: str) -> str:
    return LANGFUSE_SCORE_NAME_ALIASES.get(name, name)


def canonical_score_name(name: str) -> str:
    return _CANONICAL_SCORE_NAMES.get(name, name)


# Confidence thresholds (contract confidence; taxonomy.yaml at the pin).
_CONFIDENCE: dict[str, Any] = dict(CONTRACT["confidence"])
DEFAULT_BY_CLASS: dict[str, dict[str, float]] = {
    key: {k: float(v) for k, v in values.items()}
    for key, values in (_CONFIDENCE.get("by_class") or {}).items()
}


@dataclass
class PipelineSchema:
    """Loaded once per process; configurable thresholds from taxonomy.yaml."""

    # Global confidence defaults from the contract.
    confidence_high: float = float(_CONFIDENCE["high"])
    confidence_low: float = float(_CONFIDENCE["low"])
    retry_max: int = int(_CONFIDENCE["retry_max"])
    conflict_threshold: float = float(_CONFIDENCE["conflict_threshold"])
    judge_band_high: float = float(_CONFIDENCE["judge_band_high"])  # Lane B ceiling
    arbiter_retry_max: int = int(_CONFIDENCE["arbiter_retry_max"])
    judge_max_passes: int = int(_CONFIDENCE["judge_max_passes"])
    doc_classes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DOC_CLASSES))
    # Per-class severity overrides (taxonomy confidence.by_class). The
    # bundled mirror carries them too, so review floors are per-class even
    # without MAILROOM_TAXONOMY.
    by_class: dict[str, dict[str, float]] = field(
        default_factory=lambda: {k: dict(v) for k, v in DEFAULT_BY_CLASS.items()}
    )

    @classmethod
    def load(cls, taxonomy_path: Optional[str] = None) -> "PipelineSchema":
        schema = cls()
        path = taxonomy_path or os.environ.get("MAILROOM_TAXONOMY")
        if not path or not os.path.exists(path):
            return schema
        try:
            import yaml  # type: ignore
        except ImportError:
            return schema
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
        except Exception as exc:
            # A broken MAILROOM_TAXONOMY must be visible, not silently ignored.
            _log.error("MAILROOM_TAXONOMY %s unreadable (%s) — using bundled mirror", path, exc)
            return schema
        if not isinstance(cfg, dict):
            _log.error("MAILROOM_TAXONOMY %s is not a mapping — using bundled mirror", path)
            return schema
        conf = dict(cfg.get("confidence", {}) or {})
        by_class = conf.pop("by_class", None) or {}

        def _num(key: str, current, cast):
            raw = conf.get(key)
            if raw is None:
                return current
            try:
                return cast(raw)
            except (TypeError, ValueError):
                _log.error("MAILROOM_TAXONOMY confidence.%s=%r is not numeric — keeping %r",
                           key, raw, current)
                return current

        schema.confidence_high = _num("high", schema.confidence_high, float)
        schema.confidence_low = _num("low", schema.confidence_low, float)
        schema.retry_max = _num("retry_max", schema.retry_max, int)
        schema.conflict_threshold = _num("conflict_threshold", schema.conflict_threshold, float)
        schema.judge_band_high = _num("judge_band_high", schema.judge_band_high, float)
        schema.arbiter_retry_max = _num("arbiter_retry_max", schema.arbiter_retry_max, int)
        schema.judge_max_passes = _num("judge_max_passes", schema.judge_max_passes, int)
        if isinstance(by_class, dict):
            parsed: dict[str, dict[str, float]] = {}
            for key, overrides in by_class.items():
                if not isinstance(overrides, dict):
                    continue
                clean: dict[str, float] = {}
                for k, v in overrides.items():
                    if v is None:
                        continue
                    try:
                        clean[str(k)] = float(v)
                    except (TypeError, ValueError):
                        _log.error("MAILROOM_TAXONOMY by_class.%s.%s=%r is not numeric", key, k, v)
                parsed[str(key)] = clean
            schema.by_class = parsed
        classes = {}
        for dc in cfg.get("doc_classes", []) or []:
            if isinstance(dc, dict) and dc.get("key"):
                classes[dc["key"]] = dc.get("label", dc["key"])
        if classes:
            schema.doc_classes = classes
        return schema

    def thresholds_for(self, doc_type: Optional[str] = None) -> dict[str, float | int]:
        """Global confidence / Lane B budgets, optionally merged with by_class."""
        base: dict[str, float | int] = {
            "high": self.confidence_high,
            "low": self.confidence_low,
            "retry_max": self.retry_max,
            "conflict_threshold": self.conflict_threshold,
            "judge_band_high": self.judge_band_high,
            "arbiter_retry_max": self.arbiter_retry_max,
            "judge_max_passes": self.judge_max_passes,
        }
        if not doc_type:
            return base
        resolved = resolve_extract_class(doc_type) or doc_type
        overrides = self.by_class.get(resolved) or self.by_class.get(doc_type)
        if overrides:
            base.update(overrides)
        return base

    def specialist_for(self, doc_type: str) -> Optional[str]:
        if not doc_type:
            return None
        key = resolve_extract_class(doc_type) or doc_type
        return SPECIALIST_BY_DOC_CLASS.get(key) or SPECIALIST_BY_DOC_CLASS.get(doc_type)


def allowed_review_doc_types() -> frozenset[str]:
    return frozenset(DOC_CLASSES) | frozenset(LIVE_DOC_TYPES) | frozenset(EXTRACT_CLASS_ALIASES) | {
        UNKNOWN_DOC_TYPE,
    }


def doc_subclasses_payload() -> dict[str, list[str]]:
    return {key: list(values) for key, values in DOC_SUBCLASS_BY_CLASS.items()}


def normalize_review_doc_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip()
    if not key:
        return None
    allowed = allowed_review_doc_types()
    if key in allowed:
        return key
    lower = key.lower().replace(" ", "_")
    if lower in allowed:
        return lower
    raise ValueError(f"unknown doc_type: {value}")


def normalize_review_subclass(doc_type: Optional[str], value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    kind = str(doc_type or "")
    catalog = DOC_SUBCLASS_BY_CLASS.get(kind) or DOC_SUBCLASS_BY_CLASS.get(
        EXTRACT_CLASS_ALIASES.get(kind, kind), ()
    )
    if not catalog:
        return text
    compact = "".join(ch for ch in text.lower() if ch.isalnum())
    for token in catalog:
        if token == text:
            return token
        if "".join(ch for ch in token.lower() if ch.isalnum()) == compact:
            return token
    raise ValueError(f"unknown doc_subclass {value!r} for {kind}")


# Score names the visualizer reads by name (interpreter, metrics, eval panels).
# A pipeline rename of any of these must fail conformance, not render blank.
READ_SCORE_NAMES: frozenset[str] = frozenset(
    {
        "classification_confidence",
        "extraction_confidence",
        "llm_call_count",
        "run_aborted",
        "run_duration_seconds",
        "total_tokens",
        "estimated_cost_usd",
        *SUITE_EXTRA_SCORES,
    }
)


def contract_gaps(contract: Optional[dict[str, Any]] = None) -> list[str]:
    """What the visualizer cannot display in ``contract`` (empty = conformant).

    Checks both directions: every pipeline node, span, agent and class must
    have a floor mapping and display metadata here, and every pipeline name
    this module maps or reads must still exist upstream (a rename shows up as
    a gap, not as a silently unmapped span).
    """
    c = contract if contract is not None else CONTRACT
    gaps: list[str] = []
    spans = dict(c.get("spans") or {})
    nodes = {n["id"]: n for n in (c.get("graph") or {}).get("nodes", [])}
    non_station = {c.get("trace_name"), "pipeline-result", "answer-question"}

    for node_id, node in sorted(nodes.items()):
        stage = SPAN_STAGE_MAP.get(node_id)
        if stage is None:
            gaps.append(f"graph node {node_id!r} has no floor stage")
            continue
        # Retry nodes reuse their first-pass span (repeats fold into the retry
        # stage), so node and span need only share a phase.
        span = node.get("span")
        span_stage = SPAN_STAGE_MAP.get(span) if span else None
        if span_stage is not None and STAGE_PHASE.get(span_stage) != STAGE_PHASE.get(stage):
            gaps.append(f"node {node_id!r} and its span {span!r} land in different phases")
        if stage not in STAGE_PHASE:
            gaps.append(f"stage {stage.value!r} (node {node_id!r}) has no phase")
        if stage not in NODE_ORDER:
            gaps.append(f"stage {stage.value!r} (node {node_id!r}) is not in NODE_ORDER")
    for span in sorted(spans):
        if span not in SPAN_STAGE_MAP and span not in non_station:
            gaps.append(f"span {span!r} has no floor stage")

    start = str((c.get("graph") or {}).get("start") or GRAPH_START)
    for source, target in _graph_edges(c):
        if source != start:
            continue
        # A new entry point changes where the floor must put a fresh envelope.
        stage = SPAN_STAGE_MAP.get(target)
        if stage is None:
            gaps.append(f"start edge to {target!r} has no floor stage")
        elif stage not in {Stage.INTAKE} | RESUME_ENTRY_STAGES:
            gaps.append(
                f"start edge to {target!r} enters at {stage.value!r}, "
                "which is not a known run entry"
            )

    upstream_names = set(spans) | set(nodes)
    for name in sorted(SPAN_STAGE_MAP):
        if name.startswith(RELOADED_NODE_PREFIX):
            continue
        if name not in upstream_names:
            gaps.append(f"mapped span/node {name!r} no longer exists in the pipeline")

    for agent in sorted(c.get("agents") or []):
        if agent not in _AGENT_DISPLAY:
            gaps.append(f"agent {agent!r} has no display label")
    agents = set(c.get("agents") or [])
    for dc in c.get("doc_classes") or []:
        if dc.get("specialist") and dc["specialist"] not in agents:
            gaps.append(f"class {dc['key']!r} specialist {dc['specialist']!r} is not an agent")

    configs = {cfg["name"] for cfg in (c.get("scores") or {}).get("configs", [])}
    for name in sorted(READ_SCORE_NAMES - configs):
        gaps.append(f"score {name!r} is read by the visualizer but not registered upstream")
    for fc in c.get("failure_classes") or []:
        if fc not in _FAILURE_LABELS_LOCAL:
            gaps.append(f"failure class {fc!r} has no label")
    return gaps
