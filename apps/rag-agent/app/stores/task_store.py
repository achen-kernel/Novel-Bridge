"""
Pipeline task MySQL persistence layer.

Auto-creates novel_pipeline_task table on first use.
"""
import json
import logging
from typing import Optional

import pymysql

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS novel_pipeline_task (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    book_id BIGINT NOT NULL,
    phase VARCHAR(10) NOT NULL,
    label VARCHAR(200) NOT NULL DEFAULT '',
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    progress DOUBLE NOT NULL DEFAULT 0,
    message TEXT,
    error TEXT,
    error_code VARCHAR(50) NOT NULL DEFAULT '',
    error_detail JSON,
    result_json JSON,
    created_at DOUBLE NOT NULL,
    completed_at DOUBLE NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""


class TaskStore:
    """Persistent task storage backed by MySQL."""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
        self._ensure_table()

    def _ensure_table(self):
        with self.conn.cursor() as cursor:
            cursor.execute(CREATE_TABLE_SQL)
        self.conn.commit()

    def save(self, task_id: str, book_id: int, phase: str, label: str,
             status: str, progress: float, message: str, error: str,
             error_code: str = "", error_detail: dict = None,
             result: dict = None, created_at: float = 0,
             completed_at: float = 0):
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_pipeline_task
                     (task_id, book_id, phase, label, status, progress,
                      message, error, error_code, error_detail, result_json,
                      created_at, completed_at)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                     ON DUPLICATE KEY UPDATE
                     status=VALUES(status), progress=VALUES(progress),
                     message=VALUES(message), error=VALUES(error),
                     error_code=VALUES(error_code), error_detail=VALUES(error_detail),
                     result_json=VALUES(result_json), completed_at=VALUES(completed_at)"""
            cursor.execute(sql, (
                task_id, book_id, phase, label, status, progress,
                message, error, error_code,
                json.dumps(error_detail or {}, ensure_ascii=False),
                json.dumps(result or {}, ensure_ascii=False) if result else None,
                created_at, completed_at,
            ))
        self.conn.commit()
        logger.debug(f"Task persisted: {task_id} ({status})")

    def find(self, task_id: str) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_pipeline_task WHERE task_id = %s",
                (task_id,),
            )
            row = cursor.fetchone()
            if row:
                self._deserialize(row)
            return row

    def list_by_book(self, book_id: int, phase: str = None, limit: int = 20) -> list:
        with self.conn.cursor() as cursor:
            if phase:
                cursor.execute(
                    "SELECT * FROM novel_pipeline_task WHERE book_id = %s AND phase = %s ORDER BY created_at DESC LIMIT %s",
                    (book_id, phase, limit),
                )
            else:
                cursor.execute(
                    "SELECT * FROM novel_pipeline_task WHERE book_id = %s ORDER BY created_at DESC LIMIT %s",
                    (book_id, limit),
                )
            rows = cursor.fetchall()
            for row in rows:
                self._deserialize(row)
            return rows

    def list_recent(self, limit: int = 100) -> list:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_pipeline_task ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cursor.fetchall()
            for row in rows:
                self._deserialize(row)
            return rows

    def delete_by_book(self, book_id: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM novel_pipeline_task WHERE book_id = %s",
                (book_id,),
            )
        self.conn.commit()

    @staticmethod
    def _deserialize(row: dict):
        """Parse JSON fields in-place."""
        for field in ("error_detail", "result_json"):
            val = row.get(field)
            if isinstance(val, str):
                try:
                    row[field] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    pass
