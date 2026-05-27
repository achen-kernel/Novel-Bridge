"""Context retrieval facade."""

from __future__ import annotations

from app.context_store.schemas import ContextLevel, ContextNode


class ContextRetriever:
    async def retrieve_l1(self, book_id: int, query: str, top_k: int = 8) -> list[ContextNode]:
        return []

    async def retrieve_l2(self, book_id: int, query: str, top_k: int = 8) -> list[ContextNode]:
        return [
            node for node in await self.retrieve_l1(book_id, query, top_k)
            if node.level == ContextLevel.L2
        ]

