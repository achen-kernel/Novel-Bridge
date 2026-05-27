"""@NB-ENTRYPOINT Stage 6H MemoryInterface — abstract base for all memory layers.

Design rationale:
- ABC with clear serialize/deserialize for future DB/Redis backends.
- Each layer has a `namespace` string for routing in multi-agent scenarios.
- `clear()` resets the layer; `empty()` checks if it has meaningful content.
- All layers are optional — the system degrades gracefully if one is missing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class MemoryInterface(ABC):
    """Abstract base for all memory layers.

    Implementations must be:
    - Idempotent: repeated calls should not corrupt state.
    - Serializable: to_dict/from_dict for persistence.
    - Thread-safe for async use (callers should use asyncio.Lock if shared).
    """

    @property
    @abstractmethod
    def namespace(self) -> str:
        """Unique name for this memory layer (e.g. 'session', 'working', 'evidence')."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Reset this memory layer to initial state."""
        ...

    def empty(self) -> bool:
        """Return True if this memory layer has no meaningful content."""
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for persistence/logging.

        Override in subclasses. Default returns empty dict.
        """
        return {}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryInterface:
        """Deserialize from dict.

        Override in subclasses. Default returns a fresh instance.
        """
        raise NotImplementedError
