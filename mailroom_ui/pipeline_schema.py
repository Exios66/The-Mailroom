"""Mirror of the llm-mailroom pipeline topology.

This mirrors graph/build_graph.py + graph/routing.py + config/taxonomy.yaml of
the llm-mailroom repo so traces can be interpreted without importing that repo.
If MAILROOM_TAXONOMY points at the live taxonomy.yaml, thresholds/doc classes
are read from there instead (the topology above is data-driven there too).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from .models import Phase, Stage

SPAN_STAGE_MAP: dict[str, Stage] = {
    "ingest-document": Stage.INGEST,
    "transcribe-pdf": Stage.INGEST,
    "extract-image-text": Stage.INGEST,
    "classify-document": Stage.CLASSIFY,
    "extract-fields": Stage.EXTRACT,
    "route-for-review": Stage.HUMAN_REVIEW,
    "adjudicate-conflict": Stage.BOSS,
    "compile-report": Stage.COMPILE_REPORT,
    "write-catalog": Stage.CATALOG,
    "archive-document": Stage.ARCHIVE,
}

STAGE_PHASE: dict[Stage, Phase] = {
    Stage.INBOX: Phase.INTAKE_SORT,
    Stage.INGEST: Phase.INTAKE_SORT,
    Stage.CLASSIFY: Phase.INTAKE_SORT,
    Stage.RETRY_CLASSIFY: Phase.INTAKE_SORT,
    Stage.EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.RETRY_EXTRACT: Phase.EXTRACTION_ADJUDICATION,
    Stage.BOSS: Phase.EXTRACTION_ADJUDICATION,
    Stage.COMPILE_REPORT: Phase.REPORTING_ARCHIVE,
    Stage.CATALOG: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVE: Phase.REPORTING_ARCHIVE,
    Stage.ARCHIVED: Phase.TERMINAL,
    Stage.FAILED: Phase.TERMINAL,
    Stage.HUMAN_REVIEW: Phase.REVIEW,
    Stage.UNKNOWN: Phase.INTAKE_SORT,
}

# Node traversal order used to order spans into a routing path.
NODE_ORDER: list[Stage] = [
    Stage.INGEST,
    Stage.CLASSIFY,
    Stage.RETRY_CLASSIFY,
    Stage.EXTRACT,
    Stage.RETRY_EXTRACT,
    Stage.BOSS,
    Stage.HUMAN_REVIEW,
    Stage.COMPILE_REPORT,
    Stage.CATALOG,
    Stage.ARCHIVE,
]

# Agent display roster: key -> (label, doc classes it serves)
AGENTS: dict[str, dict[str, str]] = {
    "sorter": {"label": "Sorter", "role": "classify"},
    "contracts_specialist": {"label": "Contracts", "role": "extract"},
    "corporate_records_specialist": {"label": "Corporate", "role": "extract"},
    "due_diligence_specialist": {"label": "Due Diligence", "role": "extract"},
    "correspondence_specialist": {"label": "Correspondence", "role": "extract"},
    "compliance_specialist": {"label": "Compliance", "role": "extract"},
    "court_opinions_specialist": {"label": "Court Opinions", "role": "extract"},
    "boss": {"label": "Boss", "role": "adjudicate"},
    "reporter": {"label": "Reporter", "role": "report"},
    "judge": {"label": "Judge", "role": "evaluate"},
    "pdf_transcriber": {"label": "Transcriber", "role": "ingest"},
    "image-extractor": {"label": "Image Extractor", "role": "ingest"},
}

DOC_CLASSES: dict[str, str] = {
    "contract": "Contract / Agreement",
    "corporate_record": "Corporate Record",
    "due_diligence": "Due Diligence",
    "correspondence": "Correspondence",
    "compliance_filing": "Compliance Filing",
    "court_opinion": "Court Opinion",
}

DEFAULT_DOC_CLASSES: dict[str, str] = dict(DOC_CLASSES)

SPECIALIST_BY_DOC_CLASS: dict[str, str] = {
    "contract": "contracts_specialist",
    "corporate_record": "corporate_records_specialist",
    "due_diligence": "due_diligence_specialist",
    "correspondence": "correspondence_specialist",
    "compliance_filing": "compliance_specialist",
    "court_opinion": "court_opinions_specialist",
}


@dataclass
class PipelineSchema:
    """Loaded once per process; configurable thresholds from taxonomy.yaml."""

    confidence_high: float = 0.95
    confidence_low: float = 0.70
    retry_max: int = 1
    conflict_threshold: float = 0.3
    doc_classes: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_DOC_CLASSES))

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
        except Exception:
            return schema
        conf = cfg.get("confidence", {}) or {}
        schema.confidence_high = float(conf.get("high", schema.confidence_high))
        schema.confidence_low = float(conf.get("low", schema.confidence_low))
        schema.retry_max = int(conf.get("retry_max", schema.retry_max))
        schema.conflict_threshold = float(conf.get("conflict_threshold", schema.conflict_threshold))
        classes = {}
        for dc in cfg.get("doc_classes", []) or []:
            if isinstance(dc, dict) and dc.get("key"):
                classes[dc["key"]] = dc.get("label", dc["key"])
        if classes:
            schema.doc_classes = classes
        return schema

    def specialist_for(self, doc_type: str) -> Optional[str]:
        return SPECIALIST_BY_DOC_CLASS.get(doc_type)
