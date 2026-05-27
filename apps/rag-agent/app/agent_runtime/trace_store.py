"""Retrieval trace persistence adapter — MySQL implementation.

Stores retrieval query trace info for debugging and observability.
Table is auto-created if it does not exist (dev-friendly).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql

logger = logging.getLogger(__name__)

DDL_TRACE_TABLE = """
CREATE TABLE IF NOT EXISTS novel_retrieval_trace (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    run_id BIGINT DEFAULT NULL,
    query_text TEXT NOT NULL,
    book_id BIGINT DEFAULT NULL,
    items_json JSON,
    started_at DATETIME DEFAULT NULL,
    completed_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_retrieval_trace_run (run_id),
    KEY idx_retrieval_trace_book (book_id),
    CONSTRAINT fk_retrieval_trace_run FOREIGN KEY (run_id) REFERENCES novel_agent_run(id) ON DELETE SET NULL,
    CONSTRAINT fk_retrieval_trace_book FOREIGN KEY (book_id) REFERENCES novel_book(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


class MysqlRetrievalTraceStore:
    """MySQL adapter for retrieval trace persistence."""

    def __init__(self, conn: pymysql.Connection, *, auto_create: bool = True) -> None:
        self.conn = conn
        if auto_create:
            self._ensure_table()

    def _ensure_table(self) -> None:
        with self.conn.cursor() as c:
            c.execute(DDL_TRACE_TABLE)
            self.conn.commit()

    def create_trace(
        self,
        run_id: int,
        query: str,
        payload: dict[str, Any] | None = None,
    ) -> int:
        now = datetime.utcnow()
        book_id = (payload or {}).get("book_id")
        items_json = json.dumps((payload or {}).get("items", []), ensure_ascii=False)
        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_retrieval_trace
                   (run_id, query_text, book_id, items_json, started_at, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (run_id, query, book_id, items_json, now, now, now),
            )
            self.conn.commit()
            return c.lastrowid  # type: ignore[return-value]

    def add_item(
        self,
        trace_id: int,
        payload: dict[str, Any],
    ) -> int:
        """Append a retrieval result item to the trace's items_json array."""
        # Read current items
        with self.conn.cursor() as c:
            c.execute(
                "SELECT items_json, book_id FROM novel_retrieval_trace WHERE id = %s",
                (trace_id,),
            )
            row: dict[str, Any] | None = c.fetchone()  # type: ignore[assignment]
            if not row:
                logger.warning("Trace %s not found, cannot add item", trace_id)
                return -1

            items: list[dict[str, Any]] = []
            raw = row.get("items_json")
            if isinstance(raw, str):
                try:
                    items = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    items = []
            elif isinstance(raw, list):
                items = raw

            # Add the new item with a position
            payload["position"] = len(items)
            items.append(payload)

            now = datetime.utcnow()
            c.execute(
                "UPDATE novel_retrieval_trace SET items_json = %s, updated_at = %s WHERE id = %s",
                (json.dumps(items, ensure_ascii=False), now, trace_id),
            )
            self.conn.commit()
            return len(items) - 1

    def get_trace(self, trace_id: int) -> dict[str, Any] | None:
        with self.conn.cursor() as c:
            c.execute("SELECT * FROM novel_retrieval_trace WHERE id = %s", (trace_id,))
            row: dict[str, Any] | None = c.fetchone()  # type: ignore[assignment]
            if row and isinstance(row.get("items_json"), str):
                try:
                    row["items_json"] = json.loads(row["items_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            return row

    def get_traces_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_retrieval_trace WHERE run_id = %s ORDER BY id",
                (run_id,),
            )
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in rows:
                if isinstance(row.get("items_json"), str):
                    try:
                        row["items_json"] = json.loads(row["items_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return rows
