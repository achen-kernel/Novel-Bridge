"""
ChapterFact 存储层。
"""
import json
from datetime import datetime
from typing import Optional, List

import pymysql


class ChapterFactStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert_fact(self, book_id: int, chapter_id: int, fact_json: dict,
                    evidence_json: dict, summary: str = "",
                    parse_status: str = "NOT_CHECKED",
                    evidence_status: str = "NOT_CHECKED",
                    review_status: str = "PENDING") -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_chapter_fact
                     (book_id, chapter_id, fact_json, evidence_json, summary,
                      parse_status, evidence_status, review_status, status)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'DRAFT')
                     ON DUPLICATE KEY UPDATE
                     fact_json=VALUES(fact_json), evidence_json=VALUES(evidence_json),
                     summary=VALUES(summary), parse_status=VALUES(parse_status),
                     evidence_status=VALUES(evidence_status), review_status=VALUES(review_status),
                     status='DRAFT', updated_at=NOW()"""
            cursor.execute(sql, (
                book_id, chapter_id,
                json.dumps(fact_json, ensure_ascii=False),
                json.dumps(evidence_json, ensure_ascii=False),
                summary, parse_status, evidence_status, review_status
            ))
            # After ON DUPLICATE KEY UPDATE, lastrowid is 0 on update.
            # Query the id back to return consistently.
            cursor.execute("SELECT id FROM novel_chapter_fact WHERE chapter_id = %s", (chapter_id,))
            row = cursor.fetchone()
            return row['id'] if row else cursor.lastrowid

    def find_by_chapter(self, chapter_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM novel_chapter_fact WHERE chapter_id = %s", (chapter_id,))
            return cursor.fetchone()

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_chapter_fact WHERE book_id = %s",
                (book_id,)
            )
            return cursor.fetchall()

    def find_by_id(self, fact_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM novel_chapter_fact WHERE id = %s", (fact_id,))
            return cursor.fetchone()

    def update_review_status(self, fact_id: int, review_status: str):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE novel_chapter_fact SET review_status = %s, updated_at = NOW() WHERE id = %s",
                (review_status, fact_id)
            )
