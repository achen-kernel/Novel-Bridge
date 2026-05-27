"""Shared Agent Runtime primitives for NovelBridge.

This package is intentionally thin in Stage 3A/B. It defines contracts and
guardrails that PreprocessAgent and ReaderAgent can share without changing
existing pipeline or QA behavior.
"""

from app.agent_runtime.schemas import (
    ActionRequest,
    ActionResult,
    AgentMode,
    AgentStatus,
    EvidenceItem,
    ToolCallRecord,
)
from app.agent_runtime.state_machine import StateMachine, TransitionError
from app.agent_runtime.tool_registry import ToolRegistry

__all__ = [
    "ActionRequest",
    "ActionResult",
    "AgentMode",
    "AgentStatus",
    "EvidenceItem",
    "StateMachine",
    "ToolCallRecord",
    "ToolRegistry",
    "TransitionError",
]

