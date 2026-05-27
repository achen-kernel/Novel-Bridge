"""ReaderAgent memory system — three-layer architecture.

Layers:
  L0: SessionMemory   — cross-turn session context (book, targets, history, prefs)
  L1: WorkingMemory   — intra-execution working context (plan, tools, observations)
  L2: EvidenceMemory  — active evidence pool for current task

Each layer implements MemoryInterface, making backends swappable.
MemoryManager facade provides agent-level unified access.

Usage:
    from app.reader_agent.memory import MemoryManager
    mm = MemoryManager(session_id=123)
    mm.l0.record_turn(...)
    mm.l1.set_plan(...)
    mm.l2.add_citation(...)
"""

from app.reader_agent.memory.base import MemoryInterface
from app.reader_agent.memory.evidence_memory import EvidenceMemory
from app.reader_agent.memory.facade import MemoryManager
from app.reader_agent.memory.session_memory import SessionMemory
from app.reader_agent.memory.working_memory import WorkingMemory

__all__ = [
    "MemoryInterface",
    "MemoryManager",
    "SessionMemory",
    "WorkingMemory",
    "EvidenceMemory",
]
