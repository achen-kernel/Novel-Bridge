"""
Event Fact 存储层。
"""
import json
from typing import List, Optional

import pymysql


class EventFactStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def upsert(self, book_id: int, event_type: str, summary: str,
               participants: list = None, location: str = "",
               importance: str = "MEDIUM", chapter_id: int = None) -> int:
        """插入或更新事件事实。

        使用 book_id + event_type + summary 作为去重键。
        如果不存在则插入，存在则更新 last_chapter_id 和 importance。
        """
        with self.conn.cursor() as cursor:
            # 先查是否存在
            cursor.execute(
                "SELECT id, importance, first_chapter_id FROM novel_event_fact "
                "WHERE book_id=%s AND event_type=%s AND summary=%s",
                (book_id, event_type, summary)
            )
            existing = cursor.fetchone()
            if existing:
                # 更新：合并 importance，更新 last_chapter_id
                new_imp = self._merge_importance(existing['importance'], importance)
                cursor.execute(
                    "UPDATE novel_event_fact SET "
                    "last_chapter_id = GREATEST(COALESCE(last_chapter_id,0), %s), "
                    "importance = %s, "
                    "updated_at = NOW() "
                    "WHERE id = %s",
                    (chapter_id, new_imp, existing['id'])
                )
                return existing['id']
            else:
                # 插入新记录
                participants_json = json.dumps(participants or [], ensure_ascii=False)
                cursor.execute(
                    """INSERT INTO novel_event_fact
                       (book_id, event_type, summary, participants_json, location,
                        importance, first_chapter_id, last_chapter_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (book_id, event_type, summary, participants_json, location,
                     importance, chapter_id, chapter_id)
                )
                return cursor.lastrowid

    @staticmethod
    def _merge_importance(existing: str, new: str) -> str:
        """合并 importance：取更高优先级的"""
        level = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2, 'CRITICAL': 3}
        return existing if level.get(existing, 1) >= level.get(new, 1) else new

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_event_fact WHERE book_id = %s ORDER BY first_chapter_id",
                (book_id,))
            return cursor.fetchall()

    def find_by_type(self, book_id: int, event_type: str) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_event_fact WHERE book_id = %s AND event_type = %s ORDER BY first_chapter_id",
                (book_id, event_type))
            return cursor.fetchall()
