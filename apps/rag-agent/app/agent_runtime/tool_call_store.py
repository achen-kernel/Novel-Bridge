"""Tool call persistence — MySQL implementation.

Uses novel_tool_call table. Auto-creates on first use (dev-friendly).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql

logger = logging.getLogger(__name__)

DDL_TOOL_CALL = """
CREATE TABLE IF NOT EXISTS novel_tool_call (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id BIGINT DEFAULT NULL,
    agent_step_id BIGINT DEFAULT NULL,
    tool_name VARCHAR(100) NOT NULL,
    input_json JSON,
    output_json JSON,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    error_message TEXT,
    started_at DATETIME DEFAULT NULL,
    finished_at DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_tool_call_run (agent_run_id),
    KEY idx_tool_call_step (agent_step_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


class MysqlToolCallStore:
    """MySQL adapter for tool call recording."""

    def __init__(self, conn: pymysql.Connection, *, auto_create: bool = True) -> None:
        self.conn = conn
        if auto_create:
            self._ensure_table()

    def _ensure_table(self) -> None:
        with self.conn.cursor() as c:
            c.execute(DDL_TOOL_CALL)
            self.conn.commit()

    def create_tool_call(
        self,
        tool_name: str,
        *,
        agent_run_id: int | None = None,
        agent_step_id: int | None = None,
        input_json: dict[str, Any] | None = None,
        status: str = "PENDING",
    ) -> int:
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_tool_call
                   (agent_run_id, agent_step_id, tool_name, input_json,
                    status, started_at, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    agent_run_id,
                    agent_step_id,
                    tool_name,
                    json.dumps(input_json or {}, ensure_ascii=False),
                    status,
                    now,
                    now,
                    now,
                ),
            )
            self.conn.commit()
            return c.lastrowid  # type: ignore[return-value]

    def finish_tool_call(
        self,
        call_id: int,
        *,
        status: str = "SUCCESS",
        output_json: dict[str, Any] | None = None,
        error_message: str = "",
    ) -> None:
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """UPDATE novel_tool_call
                   SET status = %s, output_json = %s,
                       error_message = %s, finished_at = %s, updated_at = %s
                   WHERE id = %s""",
                (
                    status,
                    json.dumps(output_json or {}, ensure_ascii=False)
                    if output_json
                    else None,
                    error_message,
                    now,
                    now,
                    call_id,
                ),
            )
            self.conn.commit()

    def get_tool_calls_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_tool_call WHERE agent_run_id = %s ORDER BY id",
                (run_id,),
            )
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in rows:
                for col in ("input_json", "output_json"):
                    val = row.get(col)
                    if isinstance(val, str):
                        try:
                            row[col] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
            return rows
