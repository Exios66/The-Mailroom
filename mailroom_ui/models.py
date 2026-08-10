"""Pydantic models for The-Mailroom.

Everything here is derived exclusively from Langfuse API data (traces,
observations, scores, sessions). Nothing is fabricated by the interface.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Stage(str, Enum):
    INBOX = "inbox"
    INGEST = "ingest"
    CLASSIFY = "classify"
    RETRY_CLASSIFY = "retry_classify"
    EXTRACT = "extract"
    RETRY_EXTRACT = "retry_extract"
    BOSS = "boss"
    HUMAN_REVIEW = "review"
    COMPILE_REPORT = "report"
    CATALOG = "catalog"
    ARCHIVE = "archive"
    ARCHIVED = "archived"
    FAILED = "failed"
    UNKNOWN = "unknown"


class Phase(str, Enum):
    INTAKE_SORT = "intake_sort"            # ingest + classify
    EXTRACTION_ADJUDICATION = "extraction"  # extract + retries + boss
    REPORTING_ARCHIVE = "reporting"         # report + catalog + archive
    REVIEW = "review"                       # human review siding
    TERMINAL = "terminal"                   # archived / failed


class NodeSpan(BaseModel):
    """One node span from the Langfuse trace (verb-first names)."""

    name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    latency: Optional[float] = None          # seconds
    status: str = "unknown"                  # PENDING / SUCCESS / ERROR
    error_message: Optional[str] = None
    input: Optional[dict[str, Any]] = None
    output: Optional[dict[str, Any]] = None


class Generation(BaseModel):
    """One LLM generation observation (auto-traced by langfuse.openai)."""

    name: Optional[str] = None
    agent: Optional[str] = None              # inferred from span name
    model: Optional[str] = None
    latency: Optional[float] = None
    input: Optional[Any] = None
    output: Optional[Any] = None
    usage_total_tokens: Optional[int] = None
    usage_input_tokens: Optional[int] = None
    usage_output_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    prompt_version: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class Score(BaseModel):
    """One Langfuse score attached to the trace."""

    name: str
    value: Any
    data_type: Optional[str] = None
    comment: Optional[str] = None
    observation_id: Optional[str] = None


class PipelineRun(BaseModel):
    """A fully interpreted mailroom pipeline run for one document trace."""

    trace_id: str
    name: str = "document-pipeline"
    filename: Optional[str] = None
    matter_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    attempt: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latency: Optional[float] = None           # total trace latency s

    stage: Stage = Stage.UNKNOWN
    phase: Phase = Phase.INTAKE_SORT
    doc_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    extraction_confidence: Optional[float] = None
    review_decision: Optional[str] = None
    escalation_reason: Optional[str] = None
    error_message: Optional[str] = None
    run_aborted: bool = False

    spans: list[NodeSpan] = Field(default_factory=list)
    generations: list[Generation] = Field(default_factory=list)
    scores: dict[str, Any] = Field(default_factory=dict)
    routing_path: list[str] = Field(default_factory=list)

    verdict: Optional[str] = None             # CORRECT / PARTIAL / MISS
    quality: Optional[float] = None           # 0..1
    llm_call_count: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def retried(self) -> bool:
        return Stage.RETRY_CLASSIFY.value in self.routing_path or Stage.RETRY_EXTRACT.value in self.routing_path

    @property
    def needs_human(self) -> bool:
        return self.stage in (Stage.HUMAN_REVIEW,)


class SessionSummary(BaseModel):
    """One Langfuse session (matter in live runs, run-scoped in pilots)."""

    id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    trace_count: int = 0
    runs: list[PipelineRun] = Field(default_factory=list)


class Metrics(BaseModel):
    total_docs: int = 0
    archived: int = 0
    review: int = 0
    failed: int = 0
    in_flight: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    avg_cost_usd: float = 0.0
    avg_latency_s: float = 0.0
    p95_generation_latency_s: float = 0.0
    verdict_counts: dict[str, int] = Field(default_factory=dict)
    avg_quality: Optional[float] = None
    per_doc_type: dict[str, int] = Field(default_factory=dict)
    llm_calls: int = 0
