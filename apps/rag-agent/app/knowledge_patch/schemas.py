"""KnowledgePatch schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.agent_runtime.schemas import EvidenceItem


class PatchType(str, Enum):
    CITATION_FIX = "citation_fix"
    CONTEXT_SUMMARY_UPDATE = "context_summary_update"
    STYLE_SAMPLE_ADD = "style_sample_add"
    EVENT_ADD = "event_add"
    RELATION_STAGE_ADD = "relation_stage_add"
    SETTING_UPDATE = "setting_update"
    FORESHADOWING_LINK = "foreshadowing_link"
    ALIAS_ADD = "alias_add"
    ALIAS_BLOCK = "alias_block"
    ENTITY_SPLIT = "entity_split"
    ENTITY_MERGE = "entity_merge"
    VALIDATOR_RULE_CANDIDATE = "validator_rule_candidate"
    EVAL_CASE_CANDIDATE = "eval_case_candidate"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PatchStatus(str, Enum):
    PROPOSED = "PROPOSED"
    SCHEMA_VALIDATED = "SCHEMA_VALIDATED"
    AUTO_VALIDATED = "AUTO_VALIDATED"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    MERGED = "MERGED"
    REJECTED = "REJECTED"
    NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"
    SUPERSEDED = "SUPERSEDED"
    CANCELED = "CANCELED"


class KnowledgePatch(BaseModel):
    book_id: int
    patch_type: PatchType
    target_type: str | None = None
    target_id: int | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    risk_level: RiskLevel
    status: PatchStatus = PatchStatus.PROPOSED
    created_by: str = "reader_agent"
    run_id: int | None = None
