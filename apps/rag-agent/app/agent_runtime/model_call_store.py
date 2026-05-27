"""Model call persistence adapter — MySQL implementation.

Uses existing table: novel_model_call.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import pymysql

logger = logging.getLogger(__name__)


class MysqlModelCallStore:
    """MySQL adapter for model call recording.

    novel_model_call columns:
        id, agent_run_id, agent_step_id, book_id, chapter_id, chunk_id,
        task_type, provider, model_name, prompt_name, prompt_revision,
        schema_revision, temperature, max_tokens, input_text, output_text,
        request_json, response_json, parse_status, evidence_status,
        retry_count, duration_ms, status, error_type, error_message,
        created_at, updated_at
    """

    def __init__(self, conn: pymysql.Connection) -> None:
        self.conn = conn

    def create_model_call(
        self,
        payload: dict[str, Any],
    ) -> int:
        """Insert a new model call record. Returns the new row id."""
        now = datetime.utcnow()
        task_type = payload.get("task_type", "unknown")
        provider = payload.get("provider", "")
        model_name = payload.get("model_name", "")
        prompt_name = payload.get("prompt_name", "")
        prompt_revision = payload.get("prompt_revision", "")
        schema_revision = payload.get("schema_revision", "")
        temperature = payload.get("temperature")
        max_tokens = payload.get("max_tokens")
        input_text = payload.get("input_text", "")
        output_text = payload.get("output_text", "")
        request_json = json.dumps(
            payload.get("request_json", {}), ensure_ascii=False
        )
        response_json = json.dumps(
            payload.get("response_json", {}), ensure_ascii=False
        )
        duration_ms = payload.get("duration_ms", 0)
        status = payload.get("status", "PENDING")
        error_type = payload.get("error_type", "")
        error_message = payload.get("error_message", "")
        agent_run_id = payload.get("agent_run_id")
        agent_step_id = payload.get("agent_step_id")
        book_id = payload.get("book_id")
        chapter_id = payload.get("chapter_id")
        chunk_id = payload.get("chunk_id")

        with self.conn.cursor() as c:
            c.execute(
                """INSERT INTO novel_model_call
                   (agent_run_id, agent_step_id, book_id, chapter_id, chunk_id,
                    task_type, provider, model_name,
                    prompt_name, prompt_revision, schema_revision,
                    temperature, max_tokens,
                    input_text, output_text,
                    request_json, response_json,
                    duration_ms, status, error_type, error_message,
                    created_at, updated_at)
                   VALUES (%s, %s, %s, %s, %s,
                           %s, %s, %s,
                           %s, %s, %s,
                           %s, %s,
                           %s, %s,
                           %s, %s,
                           %s, %s, %s, %s,
                           %s, %s)""",
                (
                    agent_run_id, agent_step_id, book_id, chapter_id, chunk_id,
                    task_type, provider, model_name,
                    prompt_name, prompt_revision, schema_revision,
                    temperature, max_tokens,
                    input_text, output_text,
                    request_json, response_json,
                    duration_ms, status, error_type, error_message,
                    now, now,
                ),
            )
            self.conn.commit()
            return c.lastrowid  # type: ignore[return-value]

    def finish_model_call(
        self,
        call_id: int,
        payload: dict[str, Any],
    ) -> None:
        """Update an existing model call record with completion data."""
        now = datetime.utcnow()
        sets: list[str] = []
        values: list[Any] = []

        for key in (
            "status", "output_text", "response_json", "error_type",
            "error_message", "duration_ms", "parse_status", "evidence_status",
            "retry_count",
        ):
            if key in payload:
                if key == "response_json":
                    sets.append(f"{key} = %s")
                    values.append(json.dumps(payload[key], ensure_ascii=False))
                elif key == "retry_count":
                    sets.append(f"{key} = %s")
                    values.append(payload[key])
                else:
                    sets.append(f"{key} = %s")
                    values.append(payload[key])

        if not sets:
            return

        sets.append("updated_at = %s")
        values.append(now)
        values.append(call_id)

        with self.conn.cursor() as c:
            c.execute(
                f"UPDATE novel_model_call SET {', '.join(sets)} WHERE id = %s",
                values,
            )
            self.conn.commit()

    def get_model_call(self, call_id: int) -> dict[str, Any] | None:
        with self.conn.cursor() as c:
            c.execute("SELECT * FROM novel_model_call WHERE id = %s", (call_id,))
            row: dict[str, Any] | None = c.fetchone()  # type: ignore[assignment]
            if row:
                for json_field in ("request_json", "response_json"):
                    val = row.get(json_field)
                    if isinstance(val, str):
                        try:
                            row[json_field] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
            return row

    def get_model_calls_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with self.conn.cursor() as c:
            c.execute(
                "SELECT * FROM novel_model_call WHERE agent_run_id = %s ORDER BY id",
                (run_id,),
            )
            rows: list[dict[str, Any]] = c.fetchall()  # type: ignore[assignment]
            for row in rows:
                for json_field in ("request_json", "response_json"):
                    val = row.get(json_field)
                    if isinstance(val, str):
                        try:
                            row[json_field] = json.loads(val)
                        except (json.JSONDecodeError, TypeError):
                            pass
            return rows
