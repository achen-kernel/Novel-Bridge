"""@NB-ENTRYPOINT L2 EvidenceMemory — active evidence pool for the current task.

Wraps retrieval results and citations so modes can share evidence
without re-querying. The backed trace store (MysqlRetrievalTraceStore)
is where evidence is ultimately persisted; this is an in-memory working copy.

Lifetime: same as WorkingMemory — created per run, discarded after.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agent_runtime.schemas import EvidenceItem
from app.reader_agent.memory.base import MemoryInterface


class EvidenceMemory(MemoryInterface):
    """L2 memory: active evidence pool.

    RetrievalRunner stores results here so multiple modes/tools
    can access the same evidence without redundant queries.
    """

    def __init__(self) -> None:
        self._items: list[EvidenceItem] = []
        self._trace_id: int | None = None
        self._query: str | None = None

    @property
    def namespace(self) -> str:
        return "evidence"

    @property
    def trace_id(self) -> int | None:
        return self._trace_id

    @trace_id.setter
    def trace_id(self, value: int | None) -> None:
        self._trace_id = value

    @property
    def query(self) -> str | None:
        return self._query

    @query.setter
    def query(self, value: str | None) -> None:
        self._query = value

    @property
    def items(self) -> list[EvidenceItem]:
        return list(self._items)

    def add_item(self, item: EvidenceItem) -> None:
        self._items.append(item)

    def add_items(self, items: list[EvidenceItem]) -> None:
        self._items.extend(items)

    @property
    def citations(self) -> list[EvidenceItem]:
        """Items suitable for citation (direct/near evidence)."""
        return [
            item for item in self._items
            if item.relevance_score >= 0.5
        ]

    def clear(self) -> None:
        self._items.clear()
        self._trace_id = None
        self._query = None

    def empty(self) -> bool:
        return len(self._items) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self._trace_id,
            "query": self._query,
            "item_count": len(self._items),
            "citation_count": len(self.citations),
        }
