"""ContextStore builder contract."""

from __future__ import annotations

from app.context_store.schemas import ContextNode


class ContextBuilder:
    async def build_for_book(self, book_id: int) -> list[ContextNode]:
        return []

