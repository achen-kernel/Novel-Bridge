"""@NB-ENTRYPOINT Project + Session management — MySQL backed.

Projects contain sessions, sessions contain conversation turns.
Memory data (turns/preferences) is managed by MemoryStore separately.

Schema:
  novel_project  { id, name, created_at }
  novel_session  { id, project_id, name, created_at, updated_at }
"""
from __future__ import annotations

import logging
from typing import Any

from app.stores.memory_store import MemoryStore

logger = logging.getLogger(__name__)

_store: MemoryStore | None = None


def init_store(store: MemoryStore):
    """Initialize the global project store with a MySQL-backed MemoryStore."""
    global _store
    _store = store


def get_store() -> MemoryStore:
    """Get the global MemoryStore instance.

    Falls back to in-memory if not initialized (for backward compat).
    """
    global _store
    if _store is None:
        # Fallback: create from a fresh connection
        from app.clients.mysql_client import MysqlClient
        client = MysqlClient()
        _store = MemoryStore(client.connect())
    return _store
