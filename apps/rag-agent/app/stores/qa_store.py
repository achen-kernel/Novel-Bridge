"""
Chat / Citation 存储层。
操作 novel_chat_session, novel_chat_message, novel_citation 表。
"""
import logging
from typing import List, Dict, Optional

import pymysql

logger = logging.getLogger(__name__)


class QaStore:
    """QA 会话/消息/引用存储"""

    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    # ── Session ──

    def create_session(self, book_id: int, title: str = "") -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO novel_chat_session (book_id, title) VALUES (%s, %s)",
                (book_id, title),
            )
            return cursor.lastrowid

    def get_session(self, session_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, book_id, title, status FROM novel_chat_session WHERE id = %s",
                (session_id,),
            )
            return cursor.fetchone()

    # ── Message ──

    def get_recent_messages(self, session_id: int, limit: int = 10) -> List[dict]:
        """获取最近 N 条消息（按 message_index 正序返回）"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT id, role, content, message_index, created_at
                   FROM novel_chat_message
                   WHERE session_id = %s
                   ORDER BY message_index ASC""",
                (session_id,),
            )
            rows = cursor.fetchall()
            # 只返回最近的 limit 条（但保持正序）
            if len(rows) > limit:
                rows = rows[-limit:]
            return rows

    def get_message_count(self, session_id: int) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM novel_chat_message WHERE session_id = %s",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["cnt"] if row else 0

    def insert_user_message(
        self, session_id: int, book_id: int, content: str, msg_index: int
    ) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_chat_message
                   (session_id, book_id, role, content, message_index)
                   VALUES (%s, %s, 'user', %s, %s)""",
                (session_id, book_id, content, msg_index),
            )
            return cursor.lastrowid

    def insert_assistant_message(
        self, session_id: int, book_id: int, content: str, msg_index: int
    ) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_chat_message
                   (session_id, book_id, role, content, message_index)
                   VALUES (%s, %s, 'assistant', %s, %s)""",
                (session_id, book_id, content, msg_index),
            )
            return cursor.lastrowid

    # ── Citation ──

    def insert_citation(
        self,
        message_id: int,
        book_id: int,
        source_type: str = "chunk",
        source_id: int = 0,
        chapter_id: int = 0,
        chunk_id: Optional[int] = None,
        chapter_fact_id: Optional[int] = None,
        excerpt: str = "",
        start_offset: Optional[int] = None,
        end_offset: Optional[int] = None,
        evidence_level: str = "NEAR",
        relevance_score: float = 0.5,
    ) -> int:
        # FK safety: convert 0 to None (NULL) to avoid FK constraint failures
        safe_chapter_id = chapter_id if chapter_id and chapter_id > 0 else None
        safe_chunk_id = chunk_id if chunk_id and chunk_id > 0 else None
        safe_chapter_fact_id = chapter_fact_id if chapter_fact_id and chapter_fact_id > 0 else None
        
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_citation
                   (message_id, book_id, source_type, source_id, chapter_id,
                    chunk_id, chapter_fact_id, excerpt, start_offset, end_offset,
                    evidence_level, relevance_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    message_id,
                    book_id,
                    source_type,
                    source_id,
                    safe_chapter_id,
                    safe_chunk_id,
                    safe_chapter_fact_id,
                    excerpt,
                    start_offset,
                    end_offset,
                    evidence_level,
                    relevance_score,
                ),
            )
            return cursor.lastrowid

    def get_citations_by_message(self, message_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_citation WHERE message_id = %s",
                (message_id,),
            )
            return cursor.fetchall()
