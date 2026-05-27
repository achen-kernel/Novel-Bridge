"""Context loading contract for L0/L1/L2 routing."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LoadedContext(BaseModel):
    l0: list[dict[str, Any]] = Field(default_factory=list)
    l1: list[dict[str, Any]] = Field(default_factory=list)
    l2: list[dict[str, Any]] = Field(default_factory=list)


class ContextManager:
    """Placeholder facade. Concrete loading lives in app.context_store."""

    async def load_for_task(self, book_id: int, query: str) -> LoadedContext:
        return LoadedContext(l0=[], l1=[], l2=[])

