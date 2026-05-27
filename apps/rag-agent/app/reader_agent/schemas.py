"""ReaderAgent request and response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.agent_runtime.schemas import EvidenceItem, ToolCallStep, ToolDef
from app.reader_agent.states import ReaderState


ReaderMode = Literal["answer", "analyze", "trace", "enrich", "learn_style", "authoring"]
AnalysisType = Literal["character", "relation"]
TraceTargetType = Literal["character", "item", "setting"]
EnrichIssueType = Literal["citation_fix", "eval_case_candidate", "context_summary_update"]


# ═════════════════════════════════════════════════════════════════════
# Session tracking schemas (Stage 6F)
# ═════════════════════════════════════════════════════════════════════


class SessionTurnInfo(BaseModel):
    """Summary of a single Q&A turn for Trace Inspector."""

    mode: str
    question: str
    answer_preview: str = ""
    target_name: str | None = None
    target_type: str | None = None
    book_id: int
    run_id: int
    evidence_count: int = 0


class SessionInfo(BaseModel):
    """Session state summary for Trace Inspector."""

    session_id: int
    book_id: int | None = None
    turn_count: int = 0
    turns: list[SessionTurnInfo] = Field(default_factory=list)
    current_target_name: str | None = None
    current_target_type: str | None = None
    last_run_id: int | None = None
    context_summary: str = ""


class ReaderScope(BaseModel):
    chapter_ids: list[int] = Field(default_factory=list)
    entity_ids: list[int] = Field(default_factory=list)
    time_range: str | None = None


class ReaderOptions(BaseModel):
    provider: Literal["local", "deepseek"] = "local"
    require_citations: bool = True
    allow_patch: bool = False
    top_k: int = Field(default=12, ge=1, le=50)


class ReaderRequest(BaseModel):
    mode: ReaderMode = "answer"
    book_id: int
    question: str
    session_id: int | None = None
    analysis_type: AnalysisType | None = None
    target_name: str | None = None
    target_type: str | None = None
    trace_target_type: TraceTargetType | None = None
    chapter_range: list[int] = Field(default_factory=list)
    issue_type: EnrichIssueType | None = None
    target: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    scope: ReaderScope = Field(default_factory=ReaderScope)
    options: ReaderOptions = Field(default_factory=ReaderOptions)
    # Fix #1: /run 可接收外部 tool_sequence
    tool_sequence: list[ToolCallStep] | None = None


class ReaderResponse(BaseModel):
    run_id: int | None = None
    mode: ReaderMode
    status: ReaderState
    answer: str = ""
    citations: list[EvidenceItem] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    trace_id: int | None = None
    patches: list[dict[str, Any]] = Field(default_factory=list)
    analysis: dict[str, Any] = Field(default_factory=dict)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ── Planner schemas (Stage 6E) ────────────────────────────────────────


class PlanRequest(BaseModel):
    """Input to POST /api/reader-agent/plan."""

    book_id: int
    question: str
    session_id: int | None = None
    provider: Literal["local", "deepseek"] = "local"
    preferred_mode: str = "auto"
    model_mode: str = "deterministic"  # "deterministic" | "deepseek"


class PlanRequestPatch(BaseModel):
    """Payload patch the frontend can merge into /api/reader-agent/run."""

    mode: str
    question: str
    target_name: str
    target_type: str
    analysis_type: str | None = None
    trace_target_type: str | None = None


class PlanResponse(BaseModel):
    """Output of POST /api/reader-agent/plan."""

    mode: str
    optimized_question: str
    target_name: str
    target_type: str
    analysis_type: str | None = None
    trace_target_type: str | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    clarification: str | None = None
    request_patch: PlanRequestPatch | None = None
    tool_sequence: list[ToolCallStep] = Field(default_factory=list)
    clarification_options: list[str] | None = None
