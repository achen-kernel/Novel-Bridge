"""Agent run persistence adapter — MySQL implementation.

Uses existing tables: novel_agent_run, novel_agent_step.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql

logger = logging.getLogger(__name__)


class MysqlAgentRunStore:
    """MySQL adapter for AgentRun/AgentStep persistence.

    novel_agent_run columns:
        id, run_type, book_id, status, input_json, output_json,
        error_type, error_message, started_at, completed_at,
        created_at, updated_at

    novel_agent_step columns:
        id, agent_run_id, step_type, step_order, status,
        input_json, output_json, error_type, error_message,
        started_at, completed_at, created_at, updated_at
    """

    def __init__(self, conn: pymysql.Connection) -> None:
        self.conn = conn

    # ---- Run ----

    def create_run(
        self,
        agent_name: str,
        mode: str,
        payload: dict[str, Any] | None = None,
    ) -> int:
        run_type = f"{agent_name}/{mode}"
        input_json = json.dumps(payload or {}, ensure_ascii=False)
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_agent_run
                   (run_type, status, input_json, started_at, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (run_type, "RUNNING", input_json, now, now, now),
            )
            self.conn.commit()
            return c.lastrowid  # type: ignore[return-value]

    def finish_run(
        self,
        run_id: int,
        status: str,
        payload: dict[str, Any] | None = None,
        *,
        error_type: str = "",
        error_message: str = "",
    ) -> None:
        output_json = json.dumps(payload or {}, ensure_ascii=False)
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """UPDATE novel_agent_run
                   SET status = %s, output_json = %s,
                       error_type = %s, error_message = %s,
                       completed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (status, output_json, error_type, error_message, now, now, run_id),
            )
            self.conn.commit()

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self.conn.cursor() as c:
            c.execute("SELECT * FROM novel_agent_run WHERE id = %s", (run_id,))
            row: dict[str, Any] | None = c.fetchone()  # type: ignore[assignment]
            if row:
                if isinstance(row.get("input_json"), str):
                    row["input_json"] = json.loads(row["input_json"])
                if isinstance(row.get("output_json"), str):
                    row["output_json"] = json.loads(row["output_json"])
            return row

    def get_runs(
        self,
        run_type_prefix: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            if run_type_prefix:
                c.execute(
                    "SELECT * FROM novel_agent_run WHERE run_type LIKE %s "
                    "ORDER BY id DESC LIMIT %s OFFSET %s",
                    (run_type_prefix + "%", limit, offset),
                )
            else:
                c.execute(
                    "SELECT * FROM novel_agent_run ORDER BY id DESC LIMIT %s OFFSET %s",
                    (limit, offset),
                )
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in rows:
                if isinstance(row.get("input_json"), str):
                    try:
                        row["input_json"] = json.loads(row["input_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                if isinstance(row.get("output_json"), str):
                    try:
                        row["output_json"] = json.loads(row["output_json"])
                    except (json.JSONDecodeError, TypeError):
                        pass
            return rows

    # ---- Step ----

    def create_step(
        self,
        run_id: int,
        step_name: str,
        payload: dict[str, Any] | None = None,
        *,
        step_order: int = 0,
    ) -> int:
        input_json = json.dumps(payload or {}, ensure_ascii=False)
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_agent_step
                   (agent_run_id, step_type, step_order, status,
                    input_json, started_at, created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (run_id, step_name, step_order, "RUNNING",
                 input_json, now, now, now),
            )
            self.conn.commit()
            return c.lastrowid  # type: ignore[return-value]

    def finish_step(
        self,
        step_id: int,
        status: str,
        payload: dict[str, Any] | None = None,
        *,
        error_type: str = "",
        error_message: str = "",
    ) -> None:
        output_json = json.dumps(payload or {}, ensure_ascii=False)
        now = datetime.utcnow()
        with self.conn.cursor() as c:
            c.execute(
                """UPDATE novel_agent_step
                   SET status = %s, output_json = %s,
                       error_type = %s, error_message = %s,
                       completed_at = %s, updated_at = %s
                   WHERE id = %s""",
                (status, output_json, error_type, error_message, now, now, step_id),
            )
            self.conn.commit()

    def get_steps(self, run_id: int) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_agent_step WHERE agent_run_id = %s ORDER BY step_order",
                (run_id,),
            )
            raw: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in raw:
                if isinstance(row.get("input_json"), str):
                    row["input_json"] = json.loads(row["input_json"])
                if isinstance(row.get("output_json"), str):
                    row["output_json"] = json.loads(row["output_json"])
            return raw
