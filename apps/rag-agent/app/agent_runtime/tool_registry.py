"""Tool registration for Agent actions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


ToolCallable = Callable[..., Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolCallable] = {}

    def register(self, name: str, fn: ToolCallable | None = None):
        if fn is not None:
            self._tools[name] = fn
            return fn

        def decorator(inner: ToolCallable) -> ToolCallable:
            self._tools[name] = inner
            return inner

        return decorator

    def get(self, name: str) -> ToolCallable:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Tool is not registered: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._tools)

