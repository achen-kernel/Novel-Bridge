"""
MySQL-backed memory persistence for projects, sessions, and session memory (L0).

三张表：
- novel_project        → 项目元数据
- novel_session        → 会话元数据（属于项目）
- novel_session_memory → 会话 L0 记忆（turns / preferences / target）

使用方式和 TaskStore 一致：自动建表，CRUD + 批量持久化。
"""
import json
import logging
import time
from typing import Any

import pymysql

logger = logging.getLogger(__name__)

CREATE_TABLES_SQL = [
    """CREATE TABLE IF NOT EXISTS novel_project (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL DEFAULT '新项目',
        created_at DOUBLE NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS novel_session (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        project_id BIGINT NOT NULL,
        name VARCHAR(200) NOT NULL DEFAULT '',
        created_at DOUBLE NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        KEY idx_session_project (project_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS novel_session_memory (
        session_id BIGINT PRIMARY KEY,
        book_id INT DEFAULT NULL,
        turns_json JSON,
        preferences_json JSON,
        current_target_name VARCHAR(200) DEFAULT '',
        current_target_type VARCHAR(50) DEFAULT '',
        created_at DOUBLE NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
]


class MemoryStore:
    """MySQL persistence layer for projects, sessions, and L0 memory."""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
        self._ensure_tables()

    def _ensure_tables(self):
        with self.conn.cursor() as cursor:
            for sql in CREATE_TABLES_SQL:
                cursor.execute(sql)
        self.conn.commit()

    # ── Projects ────────────────────────────────────────────────

    def create_project(self, name: str = "新项目") -> dict:
        now = time.time()
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO novel_project (name, created_at) VALUES (%s, %s)",
                (name, now),
            )
            pid = cursor.lastrowid
        self.conn.commit()
        return {"id": pid, "name": name, "created_at": now}

    def list_projects(self) -> list[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, created_at FROM novel_project ORDER BY created_at"
            )
            return cursor.fetchall()

    def get_project(self, project_id: int) -> dict | None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, created_at FROM novel_project WHERE id = %s",
                (project_id,),
            )
            return cursor.fetchone()

    def rename_project(self, project_id: int, name: str) -> bool:
        with self.conn.cursor() as cursor:
            r = cursor.execute(
                "UPDATE novel_project SET name = %s WHERE id = %s",
                (name, project_id),
            )
        self.conn.commit()
        return r > 0

    def delete_project(self, project_id: int) -> bool:
        if project_id == 1:
            return False  # 不能删除默认项目
        with self.conn.cursor() as cursor:
            # 先删项目下的所有 session + memory
            cursor.execute(
                "DELETE FROM novel_session_memory WHERE session_id IN "
                "(SELECT id FROM novel_session WHERE project_id = %s)",
                (project_id,),
            )
            cursor.execute(
                "DELETE FROM novel_session WHERE project_id = %s",
                (project_id,),
            )
            r = cursor.execute(
                "DELETE FROM novel_project WHERE id = %s",
                (project_id,),
            )
        self.conn.commit()
        return r > 0

    # ── Sessions ────────────────────────────────────────────────

    def create_session(self, project_id: int, name: str = "") -> dict:
        now = time.time()
        name = name or f"会话 {int(now)}"
        # 确保 project 存在
        proj = self.get_project(project_id)
        if not proj:
            project_id = 1  # fallback
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO novel_session (project_id, name, created_at) VALUES (%s, %s, %s)",
                (project_id, name, now),
            )
            sid = cursor.lastrowid
        self.conn.commit()
        return {"id": sid, "project_id": project_id, "name": name, "created_at": now}

    def list_sessions(self, project_id: int) -> list[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, project_id, name, created_at, updated_at "
                "FROM novel_session WHERE project_id = %s ORDER BY updated_at DESC",
                (project_id,),
            )
            rows = cursor.fetchall()
            # Convert datetime to timestamp for json
            for r in rows:
                if isinstance(r.get("updated_at"), str):
                    r["updated_at"] = time.time()
            return rows

    def get_session(self, session_id: int) -> dict | None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, project_id, name, created_at FROM novel_session WHERE id = %s",
                (session_id,),
            )
            return cursor.fetchone()

    def rename_session(self, session_id: int, name: str) -> bool:
        with self.conn.cursor() as cursor:
            r = cursor.execute(
                "UPDATE novel_session SET name = %s WHERE id = %s",
                (name, session_id),
            )
        self.conn.commit()
        return r > 0

    def touch_session(self, session_id: int):
        """Update session's updated_at timestamp."""
        import datetime
        with self.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE novel_session SET updated_at = NOW() WHERE id = %s",
                (session_id,),
            )
        self.conn.commit()

    def delete_session(self, session_id: int) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM novel_session_memory WHERE session_id = %s",
                (session_id,),
            )
            r = cursor.execute(
                "DELETE FROM novel_session WHERE id = %s",
                (session_id,),
            )
        self.conn.commit()
        return r > 0

    # ── Session Memory (L0) ─────────────────────────────────────

    def save_session_memory(self, session_id: int, data: dict):
        """Save/update L0 memory for a session.

        data format:
        {
            "book_id": int | None,
            "turns_json": list[dict],
            "preferences_json": dict,
            "current_target_name": str,
            "current_target_type": str,
            "created_at": float,
        }
        """
        created_at = data.get("created_at", time.time())
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_session_memory
                     (session_id, book_id, turns_json, preferences_json,
                      current_target_name, current_target_type, created_at)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)
                     ON DUPLICATE KEY UPDATE
                     book_id=VALUES(book_id),
                     turns_json=VALUES(turns_json),
                     preferences_json=VALUES(preferences_json),
                     current_target_name=VALUES(current_target_name),
                     current_target_type=VALUES(current_target_type)"""
            cursor.execute(sql, (
                session_id,
                data.get("book_id"),
                json.dumps(data.get("turns", []), ensure_ascii=False),
                json.dumps(data.get("preferences", {}), ensure_ascii=False),
                data.get("current_target_name", ""),
                data.get("current_target_type", ""),
                created_at,
            ))
        self.conn.commit()

    def load_session_memory(self, session_id: int) -> dict | None:
        """Load L0 memory for a session. Returns None if not found."""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_session_memory WHERE session_id = %s",
                (session_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            result = {
                "book_id": row.get("book_id"),
                "turns": json.loads(row.get("turns_json") or "[]"),
                "preferences": json.loads(row.get("preferences_json") or "{}"),
                "current_target_name": row.get("current_target_name", ""),
                "current_target_type": row.get("current_target_type", ""),
                "created_at": row.get("created_at", time.time()),
            }
            return result

    def delete_session_memory(self, session_id: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM novel_session_memory WHERE session_id = %s",
                (session_id,),
            )
        self.conn.commit()

    # ── Batch operations ────────────────────────────────────────

    def save_all_memories(self, managers: dict):
        """Persist all in-memory MemoryManagers to MySQL.

        Called on server shutdown or periodic timer.
        """
        for session_id, mm in managers.items():
            try:
                memory_data = mm.l0.to_dict()
                memory_data["created_at"] = getattr(mm.l0, "_created_at", time.time())
                self.save_session_memory(session_id, memory_data)
            except Exception as e:
                logger.warning("Failed to persist memory for session %s: %s", session_id, e)

    def restore_all_memories(self, managers: dict):
        """Load all session memories from MySQL into in-memory managers.

        Called on server startup. Only loads sessions that have existing memory data.
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT session_id FROM novel_session_memory ORDER BY session_id"
            )
            rows = cursor.fetchall()
        for row in rows:
            sid = row["session_id"]
            try:
                data = self.load_session_memory(sid)
                if data and sid in managers:
                    mm = managers[sid]
                    # Restore turns
                    from app.reader_agent.memory.session_memory import SessionTurn
                    for t in data.get("turns", []):
                        turn = SessionTurn(
                            mode=t.get("mode", ""),
                            question=t.get("question", ""),
                            optimized_question=t.get("optimized_question", t.get("question", "")),
                            answer_preview=t.get("answer_preview", ""),
                            target_name=t.get("target_name"),
                            target_type=t.get("target_type"),
                            book_id=t.get("book_id", 0),
                            run_id=t.get("run_id", 0),
                            evidence_ids=t.get("evidence_ids", []),
                            provider=t.get("provider", "local"),
                            timestamp=t.get("timestamp", time.time()),
                        )
                        mm.l0.record_turn(turn)
                    # Restore preferences
                    prefs = data.get("preferences", {})
                    if prefs:
                        from app.reader_agent.memory.session_memory import UserPreferences
                        mm.l0.preferences = UserPreferences.from_dict(prefs)
                    # Restore target
                    if data.get("current_target_name"):
                        mm.l0._current_target_name = data["current_target_name"]
                    if data.get("current_target_type"):
                        mm.l0._current_target_type = data["current_target_type"]
            except Exception as e:
                logger.warning("Failed to restore memory for session %s: %s", sid, e)
