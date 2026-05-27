"""@NB-ENTRYPOINT L1 WorkingMemory — intra-execution working state.

Tracks the current plan, tool call sequence, observations, and
pending clarifications during a single think→act→observe cycle.

Lifetime: created at agent.run() start, destroyed at agent.run() end.
Never persisted — purely ephemeral.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.reader_agent.memory.base import MemoryInterface


@dataclass
class ToolCallRecord:
    """Record of a tool call during execution."""

    tool_name: str
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    status: str = "pending"  # pending | running | success | failed
    error: str | None = None
    duration_ms: float | None = None


@dataclass
class ClarificationRecord:
    """A pending clarification the agent needs user input for."""

    question: str
    options: list[str] | None = None
    resolved: bool = False


class WorkingMemory(MemoryInterface):
    """L1 memory: single-run working context.

    NOT persisted — lives only during one agent.run() cycle.
    """

    def __init__(self) -> None:
        self._plan: dict[str, Any] | None = None
        self._tool_calls: list[ToolCallRecord] = []
        self._observations: list[str] = []
        self._pending_clarifications: list[ClarificationRecord] = []
        self._status: str = "idle"
        # idle → planning → executing → observing → done | failed

    @property
    def namespace(self) -> str:
        return "working"

    @property
    def plan(self) -> dict[str, Any] | None:
        return self._plan

    def set_plan(self, plan: dict[str, Any]) -> None:
        self._plan = plan
        self._status = "planning"

    @property
    def status(self) -> str:
        return self._status

    @status.setter
    def status(self, value: str) -> None:
        self._status = value

    @property
    def tool_calls(self) -> list[ToolCallRecord]:
        return list(self._tool_calls)

    def record_tool_call(self, record: ToolCallRecord) -> None:
        self._tool_calls.append(record)

    @property
    def observations(self) -> list[str]:
        return list(self._observations)

    def add_observation(self, obs: str) -> None:
        self._observations.append(obs)

    @property
    def pending_clarifications(self) -> list[ClarificationRecord]:
        return [c for c in self._pending_clarifications if not c.resolved]

    def add_clarification(self, question: str, options: list[str] | None = None) -> None:
        self._pending_clarifications.append(
            ClarificationRecord(question=question, options=options)
        )

    def resolve_clarification(self, index: int = 0) -> None:
        """Mark the nth pending clarification as resolved."""
        unresolved = self.pending_clarifications
        if 0 <= index < len(unresolved):
            unresolved[index].resolved = True

    def clear(self) -> None:
        self._plan = None
        self._tool_calls.clear()
        self._observations.clear()
        self._pending_clarifications.clear()
        self._status = "idle"

    def empty(self) -> bool:
        return self._plan is None and not self._tool_calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self._plan,
            "status": self._status,
            "tool_calls": [
                {
                    "tool_name": tc.tool_name,
                    "status": tc.status,
                    "error": tc.error,
                    "duration_ms": tc.duration_ms,
                }
                for tc in self._tool_calls
            ],
            "observations": self._observations[-5:],
            "pending_clarifications": [
                {"question": c.question, "options": c.options}
                for c in self.pending_clarifications
            ],
        }
