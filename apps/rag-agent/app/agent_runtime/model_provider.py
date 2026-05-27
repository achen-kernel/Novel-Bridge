"""Model provider contract used by planners and answer generation."""

from __future__ import annotations

from typing import Protocol


class ModelProvider(Protocol):
    async def complete(self, prompt: str, *, schema_name: str | None = None) -> str:
        ...

