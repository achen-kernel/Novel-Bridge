import json
from typing import List, Optional
import pymysql


class RelationFactStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def upsert(self, book_id: int, source_name: str, target_name: str,
               relation_type: str, relation_family: str = "OTHER",
               polarity: str = "NEUTRAL", confidence: float = 0.0,
               chapter_id: int = None) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_relation_fact 
                   (book_id, relation_type, relation_family, source_entity_name, target_entity_name,
                    polarity, confidence, strength, first_chapter_id, last_chapter_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 1, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   strength = strength + 1,
                   confidence = (confidence + %s) / 2,
                   last_chapter_id = GREATEST(COALESCE(last_chapter_id, 0), %s),
                   updated_at = NOW()""",
                (book_id, relation_type, relation_family, source_name, target_name,
                 polarity, confidence, chapter_id, chapter_id,
                 confidence, chapter_id))
            return cursor.lastrowid

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_relation_fact WHERE book_id = %s ORDER BY strength DESC",
                (book_id,))
            return cursor.fetchall()

    def find_by_entity(self, book_id: int, entity_name: str) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM novel_relation_fact 
                   WHERE book_id = %s AND (source_entity_name = %s OR target_entity_name = %s)
                   ORDER BY strength DESC""",
                (book_id, entity_name, entity_name))
            return cursor.fetchall()
