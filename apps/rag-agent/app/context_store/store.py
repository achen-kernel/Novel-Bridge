"""ContextStore persistence contract."""

from __future__ import annotations

from typing import Protocol

from app.context_store.schemas import ContextNode


class ContextStore(Protocol):
    def upsert_node(self, node: ContextNode) -> str:
        ...

    def get_node(self, uri: str) -> ContextNode | None:
        ...

