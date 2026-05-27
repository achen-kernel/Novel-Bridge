"""ContextStore schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ContextLevel(str, Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


class ContextNode(BaseModel):
    uri: str
    book_id: int
    level: ContextLevel
    node_type: str
    title: str = ""
    content: str = ""
    source_hash: str | None = None
    version: dict[str, Any] = Field(default_factory=dict)

    @property
    def can_be_cited(self) -> bool:
        return self.level == ContextLevel.L2
