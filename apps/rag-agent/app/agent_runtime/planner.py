"""Planner contract.

LLM planners may propose actions, but state machines and tool schemas decide
what can actually execute.
"""

from __future__ import annotations

from app.agent_runtime.schemas import ActionRequest


class StaticPlanner:
    def __init__(self, actions: list[str]) -> None:
        self.actions = actions

    def plan(self, *, book_id: int | None = None, payload: dict | None = None) -> list[ActionRequest]:
        payload = payload or {}
        return [
            ActionRequest(name=action, book_id=book_id, payload=payload)
            for action in self.actions
        ]

