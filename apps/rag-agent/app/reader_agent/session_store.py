"""@NB-ENTRYPOINT Stage 6F in-memory session store for ReaderAgent.

DEPRECATED — fully replaced by app.reader_agent.memory (MemoryManager + MemoryInterface).
No code imports this module anymore. Kept as reference.
Remove when the next stage ships. See app/reader_agent/memory/ for current implementation.

Stores recent questions, answers, targets, evidence IDs per session.
Thread-safe for async use via asyncio.Lock.

Design: in-memory dict, no TTL, no persistence.
Sessions expire on server restart — acceptable for demo.
Future: add DB-backed or Redis-backed store for production.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionTurn:
    """A single Q&A turn in a session."""

    mode: str
    question: str
    optimized_question: str
    answer_preview: str
    target_name: str | None
    target_type: str | None
    book_id: int
    run_id: int
    evidence_ids: list[int]
    timestamp: float = field(default_factory=time.time)


@dataclass
class SessionState:
    """Session memory state."""

    session_id: int
    book_id: int | None = None
    turns: list[SessionTurn] = field(default_factory=list)
    current_target_name: str | None = None
    current_target_type: str | None = None
    current_book_id: int | None = None
    last_run_id: int | None = None
    last_evidence_ids: list[int] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    @property
    def last_turn(self) -> SessionTurn | None:
        return self.turns[-1] if self.turns else None

    @property
    def recent_questions(self) -> list[str]:
        return [t.question for t in self.turns[-5:]]

    @property
    def recent_targets(self) -> list[str]:
        targets: list[str] = []
        for t in self.turns[-5:]:
            if t.target_name and t.target_name not in targets:
                targets.append(t.target_name)
        return targets

    def add_turn(self, turn: SessionTurn) -> None:
        self.turns.append(turn)
        self.current_target_name = turn.target_name or self.current_target_name
        self.current_target_type = turn.target_type or self.current_target_type
        self.current_book_id = turn.book_id
        self.last_run_id = turn.run_id
        self.last_evidence_ids = turn.evidence_ids
        self.updated_at = time.time()

    def get_context_summary(self) -> str:
        """Return a human-readable summary of session context."""
        lines: list[str] = []
        if self.current_book_id:
            book_names = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}
            lines.append(f"当前书籍：{book_names.get(self.current_book_id, str(self.current_book_id))}")
        if self.current_target_name:
            lines.append(f"当前目标：{self.current_target_name} ({self.current_target_type or 'unknown'})")
        if self.turns:
            lines.append(f"已提问 {len(self.turns)} 轮")
            lines.append(f"上一轮问题：{self.turns[-1].question}")
            if self.turns[-1].mode:
                lines.append(f"上一轮模式：{self.turns[-1].mode}")
        return " | ".join(lines)


_next_session_id = 1
_sessions: dict[int, SessionState] = {}
_lock = asyncio.Lock()


async def get_or_create_session(session_id: int | None, default_book_id: int = 6) -> SessionState:
    """Get existing session or create a new one."""
    global _next_session_id
    async with _lock:
        if session_id and session_id in _sessions:
            return _sessions[session_id]
        new_id = session_id or _next_session_id
        _next_session_id = max(_next_session_id, new_id + 1)
        session = SessionState(session_id=new_id, book_id=default_book_id)
        _sessions[new_id] = session
        return session


async def record_turn(
    session_id: int,
    turn: SessionTurn,
) -> None:
    """Record a turn in session memory."""
    async with _lock:
        if session_id in _sessions:
            _sessions[session_id].add_turn(turn)


async def get_session(session_id: int) -> SessionState | None:
    """Get session by ID, or None."""
    async with _lock:
        return _sessions.get(session_id)


async def clear_session(session_id: int) -> None:
    """Clear a session's history but keep ID."""
    async with _lock:
        if session_id in _sessions:
            _sessions[session_id].turns.clear()
            _sessions[session_id].current_target_name = None
            _sessions[session_id].current_target_type = None
            _sessions[session_id].updated_at = time.time()


async def list_sessions() -> list[dict[str, Any]]:
    """List all active sessions (for Trace Inspector)."""
    async with _lock:
        return [
            {
                "session_id": s.session_id,
                "book_id": s.book_id,
                "turn_count": len(s.turns),
                "last_question": s.turns[-1].question if s.turns else None,
                "last_mode": s.turns[-1].mode if s.turns else None,
                "current_target": s.current_target_name,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in _sessions.values()
        ]
