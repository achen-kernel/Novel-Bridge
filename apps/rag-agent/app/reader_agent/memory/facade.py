"""@NB-ENTRYPOINT MemoryManager — unified facade for all memory layers.

Agent code interacts with memory through this single entry point.
Individual layers are accessible as `.l0`, `.l1`, `.l2`.

Extensibility:
  - To swap SessionMemory backend: subclass SessionMemory, override _save/_load.
  - To add a new memory layer: implement MemoryInterface, register in MemoryManager.
  - To persist all layers: override `save_all()` / `load_all()`.

Usage:
    mm = MemoryManager(session_id=123)
    mm.l0.record_turn(turn)
    mm.l1.set_plan(plan_dict)
    mm.l2.add_item(evidence_item)
    mm.save_all()  # future: persist to DB
"""

from __future__ import annotations

from typing import Any, Optional

from app.reader_agent.memory.base import MemoryInterface
from app.reader_agent.memory.evidence_memory import EvidenceMemory
from app.reader_agent.memory.session_memory import SessionMemory
from app.reader_agent.memory.working_memory import WorkingMemory


class MemoryManager:
    """Facade over L0/L1/L2 memory layers.

    Each layer is lazy-created on first access.
    The manager can `reset_run()` (clear L1+L2) while keeping L0.

    If a memory_store is provided, L0 mutations are auto-persisted.
    """

    def __init__(self, session_id: int, memory_store: Any = None) -> None:
        self._session_id = session_id
        self._memory_store = memory_store
        self._l0: SessionMemory | None = None
        self._l1: WorkingMemory | None = None
        self._l2: EvidenceMemory | None = None

    # ── Layer accessors ─────────────────────────────────────────────

    @property
    def l0(self) -> SessionMemory:
        """L0 SessionMemory — cross-turn context (lazy init)."""
        if self._l0 is None:
            self._l0 = SessionMemory(self._session_id)
            self._l0._store = self._memory_store
        return self._l0

    @property
    def l1(self) -> WorkingMemory:
        """L1 WorkingMemory — per-run working state (lazy init)."""
        if self._l1 is None:
            self._l1 = WorkingMemory()
        return self._l1

    @property
    def l2(self) -> EvidenceMemory:
        """L2 EvidenceMemory — per-run evidence pool (lazy init)."""
        if self._l2 is None:
            self._l2 = EvidenceMemory()
        return self._l2

    # ── Lifecycle ───────────────────────────────────────────────────

    def reset_run(self) -> None:
        """Clear L1 + L2 for a new execution cycle. Preserves L0."""
        self._l1 = WorkingMemory()
        self._l2 = EvidenceMemory()

    def clear_all(self) -> None:
        """Clear all layers."""
        self._l0 = None
        self._l1 = None
        self._l2 = None

    # ── Batch operations ────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize all layers for logging/Trace Inspector."""
        result: dict[str, Any] = {"session_id": self._session_id}
        for layer in ("l0", "l1", "l2"):
            mem = getattr(self, layer, None)
            if mem and not mem.empty():
                result[layer] = mem.to_dict()
            else:
                result[layer] = None
        return result

    # ── Future: persistence hooks ───────────────────────────────────

    def save_all(self) -> None:
        """Persist all layers. Override for DB/Redis backend.

        Default is no-op (in-memory only).
        """
        pass

    def load_all(self) -> None:
        """Restore all layers from persistence. Override for DB/Redis.

        Default is no-op (in-memory only, starts fresh).
        """
        pass
