"""Schemas for PreprocessAgent requests, responses, and plans."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.preprocess_agent.states import PreprocessState


# ---- Execute ----

class PreprocessRequest(BaseModel):
    book_id: int
    start_state: PreprocessState = PreprocessState.NEW
    target_state: PreprocessState = PreprocessState.DONE
    options: dict[str, Any] = Field(default_factory=dict)
    # Confirm token for dangerous action guard (4B.2).
    # Deterministic SHA256 of book_id+start_state+target_state+dangerous_actions.
    # This is a safety guardrail, not an auth system.
    confirm_token: str = ""


class PreprocessResult(BaseModel):
    book_id: int
    status: PreprocessState
    run_id: int | None = None
    completed_actions: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    required_confirm_token: str = ""  # set when token is missing/wrong


# ---- Plan / dry-run ----

class PreprocessPlanStep(BaseModel):
    action: str  # PreprocessState value
    will_run: bool
    skip_reason: str = ""
    danger_level: str = "low"  # low|medium|high|critical
    required_confirmation: bool = False
    estimated_effect: dict[str, Any] = Field(default_factory=dict)
    needs_schema_support: bool = False
    warnings: list[str] = Field(default_factory=list)


class PreprocessPlanResponse(BaseModel):
    book_id: int
    start_state: str
    target_state: str
    steps: list[PreprocessPlanStep] = Field(default_factory=list)
    has_high_risk: bool = False
    has_critical_risk: bool = False
    warnings: list[str] = Field(default_factory=list)
    required_confirm_token: str = ""  # set when dangerous actions present
    confirmation_hint: str = ""  # human-readable explanation


class PreprocessPlanRequest(BaseModel):
    book_id: int
    start_state: PreprocessState = PreprocessState.NEW
    target_state: PreprocessState = PreprocessState.DONE
