"""@NB-ENTRYPOINT L0 SessionMemory — cross-turn session context.

Replaces the old `session_store.py` SessionState dataclass.
Keeps backward-compatible `get_context_summary()` and `record_turn()`.

Designed for future backend swap:
- Implement `_save()` / `_load()` to persist to MySQL/Redis.
- The in-memory dict is the default fallback.

Lifetime: across multiple user requests within a session.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from app.reader_agent.memory.base import MemoryInterface


@dataclass
class SessionTurn:
    """A single Q&A turn. Immutable by convention."""

    mode: str
    question: str
    optimized_question: str
    answer_preview: str
    target_name: str | None
    target_type: str | None
    book_id: int
    run_id: int
    evidence_ids: list[int]
    provider: str = "local"
    timestamp: float = field(default_factory=time.time)


@dataclass
class UserPreferences:
    """Per-session user preferences. Extensible by design."""

    provider: str = "local"  # "local" | "deepseek"
    concise: bool = False  # True = shorter answers
    debug_visible: bool = False
    top_k: int = 12

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "concise": self.concise,
            "debug_visible": self.debug_visible,
            "top_k": self.top_k,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> UserPreferences:
        return cls(
            provider=d.get("provider", "local"),
            concise=d.get("concise", False),
            debug_visible=d.get("debug_visible", False),
            top_k=d.get("top_k", 12),
        )


_BOOK_NAMES = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}


class SessionMemory(MemoryInterface):
    """L0 memory: persistent cross-turn context.

    Default backend: in-memory dict.
    To switch to DB: override _load() / _save() in a subclass.
    """

    def __init__(self, session_id: int) -> None:
        self._session_id = session_id
        self._book_id: int | None = None
        self._turns: list[SessionTurn] = []
        self._current_target_name: str | None = None
        self._current_target_type: str | None = None
        self._preferences: UserPreferences = UserPreferences()
        self._created_at: float = time.time()
        self._updated_at: float = time.time()
        # Lazy-loaded store reference — set by MemoryManager
        self._store: Any = None

    @property
    def namespace(self) -> str:
        return f"session_{self._session_id}"

    @property
    def session_id(self) -> int:
        return self._session_id

    @property
    def book_id(self) -> int | None:
        return self._book_id

    @book_id.setter
    def book_id(self, value: int | None) -> None:
        self._book_id = value
        self._touch()

    @property
    def current_target_name(self) -> str | None:
        return self._current_target_name

    @property
    def current_target_type(self) -> str | None:
        return self._current_target_type

    @property
    def preferences(self) -> UserPreferences:
        return self._preferences

    @preferences.setter
    def preferences(self, value: UserPreferences) -> None:
        self._preferences = value
        self._touch()

    @property
    def turn_count(self) -> int:
        return len(self._turns)

    @property
    def turns(self) -> list[SessionTurn]:
        return list(self._turns)

    @property
    def last_turn(self) -> SessionTurn | None:
        return self._turns[-1] if self._turns else None

    @property
    def recent_questions(self) -> list[str]:
        return [t.question for t in self._turns[-5:]]

    @property
    def recent_targets(self) -> list[str]:
        targets: list[str] = []
        for t in self._turns[-5:]:
            if t.target_name and t.target_name not in targets:
                targets.append(t.target_name)
        return targets

    # ── record ──────────────────────────────────────────────────────

    def record_turn(self, turn: SessionTurn) -> None:
        """Record a Q&A turn and update current target/book."""
        self._turns.append(turn)
        if turn.target_name:
            self._current_target_name = turn.target_name
        if turn.target_type:
            self._current_target_type = turn.target_type
        if turn.book_id:
            self._book_id = turn.book_id
        self._touch()

    # ── context ─────────────────────────────────────────────────────

    def get_context_summary(self) -> str:
        """Human-readable summary for Trace Inspector and planner."""
        parts: list[str] = []
        if self._book_id:
            name = _BOOK_NAMES.get(self._book_id, str(self._book_id))
            parts.append(f"当前书籍：{name}")
        if self._current_target_name:
            parts.append(f"当前目标：{self._current_target_name} ({self._current_target_type or 'unknown'})")
        if self._turns:
            parts.append(f"已提问 {len(self._turns)} 轮")
            last = self._turns[-1]
            parts.append(f"上一轮问题：{last.question}")
            if last.mode:
                parts.append(f"上一轮模式：{last.mode}")
        return " | ".join(parts)

    # ── clear ───────────────────────────────────────────────────────

    def clear(self) -> None:
        self._turns.clear()
        self._current_target_name = None
        self._current_target_type = None
        self._preferences = UserPreferences()
        self._touch()

    def empty(self) -> bool:
        return len(self._turns) == 0

    # ── persistence hooks (override for DB/Redis) ───────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self._session_id,
            "book_id": self._book_id,
            "turn_count": self.turn_count,
            "current_target_name": self._current_target_name,
            "current_target_type": self._current_target_type,
            "preferences": self._preferences.to_dict(),
            "turns": [
                {
                    "mode": t.mode,
                    "question": t.question[:80],
                    "target_name": t.target_name,
                    "target_type": t.target_type,
                    "book_id": t.book_id,
                    "run_id": t.run_id,
                    "provider": t.provider,
                }
                for t in self._turns[-10:]  # last 10 only for serialization
            ],
        }

    def _touch(self) -> None:
        """Called on every mutation. Auto-persists to MySQL if store is attached."""
        self._updated_at = time.time()
        if self._store is not None:
            try:
                self._store.save_session_memory(self._session_id, self.to_dict())
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(
                    "SessionMemory auto-save failed for %s: %s", self._session_id, e)
