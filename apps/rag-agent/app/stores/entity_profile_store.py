"""
Entity Profile 存储层。
"""
import json
from typing import List, Optional

import pymysql


class EntityProfileStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
    
    def insert_profile(self, book_id: int, canonical_name: str,
                       entity_type: str = "CHARACTER",
                       description: str = "",
                       aliases: List[str] = None,
                       first_chapter_id: int = None,
                       last_chapter_id: int = None,
                       mention_count: int = 0,
                       source: str = "EXTRACTED") -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_entity_profile 
                     (book_id, canonical_name, entity_type, description,
                      aliases_json, first_chapter_id, last_chapter_id,
                      mention_count, source)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                     ON DUPLICATE KEY UPDATE
                     mention_count = mention_count + %s,
                     last_chapter_id = GREATEST(COALESCE(last_chapter_id, 0), %s),
                     first_chapter_id = LEAST(COALESCE(first_chapter_id, 999999999), %s),
                     description = COALESCE(NULLIF(%s, ''), description),
                     updated_at = NOW()"""
            aliases_json = json.dumps(aliases or [], ensure_ascii=False)
            chapter_val = first_chapter_id or 0
            cursor.execute(sql, (book_id, canonical_name, entity_type, description,
                                aliases_json, chapter_val, chapter_val,
                                mention_count, source,
                                mention_count, chapter_val, chapter_val, description))
            return cursor.lastrowid
    
    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_entity_profile WHERE book_id = %s ORDER BY mention_count DESC",
                (book_id,)
            )
            return cursor.fetchall()
    
    def find_by_name(self, book_id: int, name: str) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_entity_profile WHERE book_id = %s AND canonical_name = %s",
                (book_id, name)
            )
            return cursor.fetchone()
    
    def find_by_id(self, profile_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM novel_entity_profile WHERE id = %s", (profile_id,))
            return cursor.fetchone()
    
    def update_description(self, profile_id: int, description: str):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "UPDATE novel_entity_profile SET description = %s WHERE id = %s",
                (description, profile_id)
            )
    
    def delete_by_book(self, book_id: int):
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM novel_entity_profile WHERE book_id = %s", (book_id,))
