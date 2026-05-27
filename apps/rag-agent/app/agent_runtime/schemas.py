"""Shared schemas for Agent runtime contracts."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    PREPROCESS = "preprocess"
    ANSWER = "answer"
    ANALYZE = "analyze"
    TRACE = "trace"
    ENRICH = "enrich"
    LEARN_STYLE = "learn_style"
    AUTHORING = "authoring"


class AgentStatus(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    NEED_REVIEW = "NEED_REVIEW"
    NEED_FOLLOWUP = "NEED_FOLLOWUP"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class EvidenceLevel(str, Enum):
    DIRECT = "DIRECT"
    NEAR = "NEAR"
    INFERRED = "INFERRED"


EvidenceSourceType = Literal[
    "chunk",
    "chapter_fact",
    "entity",
    "relation",
    "event",
    "citation",
]


class EvidenceItem(BaseModel):
    """L2 evidence item. L0/L1 context summaries must not use this schema."""

    source_type: EvidenceSourceType
    source_id: int
    chapter_id: int | None = None
    excerpt: str = ""
    evidence_level: EvidenceLevel = EvidenceLevel.NEAR
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)


class ActionRequest(BaseModel):
    """Planner-proposed action. StateMachine still validates actual execution."""

    name: str
    run_id: int | None = None
    book_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    name: str
    status: AgentStatus = AgentStatus.DONE
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    tool_name: str
    run_id: int | None = None
    step_id: int | None = None
    input_json: dict[str, Any] = Field(default_factory=dict)
    output_json: dict[str, Any] | None = None
    status: str = "PENDING"
    error: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None


# ── Tool orchestration (P0) ──────────────────────────────────────────


class ToolDef(BaseModel):
    """Tool definition for agent orchestration."""
    name: str
    description: str
    input_example: dict[str, Any] = Field(default_factory=dict)


class ToolCallStep(BaseModel):
    """A single step in a tool execution sequence."""
    tool_name: str
    params: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    fallback_tool: str | None = None
