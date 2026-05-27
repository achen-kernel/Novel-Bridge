"""
Entity Mention 存储层。
"""
import json
from typing import List, Optional

import pymysql


class EntityMentionStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
    
    def insert_mention(self, book_id: int, chapter_id: int, chunk_id: int,
                       surface_text: str, normalized_name: str = "",
                       entity_type: str = "CHARACTER",
                       mention_role: str = "UNCERTAIN",
                       confidence: float = 0.0,
                       is_generic: bool = False,
                       do_not_merge_globally: bool = False,
                       evidence_text: str = "") -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_entity_mention 
                     (book_id, chapter_id, chunk_id, surface_text, normalized_name,
                      entity_type, mention_role, confidence, is_generic,
                      do_not_merge_globally, evidence_text)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            cursor.execute(sql, (book_id, chapter_id, chunk_id, surface_text,
                                normalized_name, entity_type, mention_role,
                                confidence, int(is_generic),
                                int(do_not_merge_globally), evidence_text))
            return cursor.lastrowid
    
    def insert_mentions_batch(self, mentions: List[dict]) -> int:
        """批量插入"""
        with self.conn.cursor() as cursor:
            count = 0
            for m in mentions:
                cursor.execute(
                    """INSERT INTO novel_entity_mention 
                       (book_id, chapter_id, chunk_id, surface_text, normalized_name,
                        entity_type, mention_role, confidence, is_generic,
                        do_not_merge_globally, evidence_text)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (m['book_id'], m['chapter_id'], m.get('chunk_id'),
                     m['surface_text'], m.get('normalized_name', ''),
                     m.get('entity_type', 'CHARACTER'),
                     m.get('mention_role', 'UNCERTAIN'),
                     m.get('confidence', 0.0),
                     int(m.get('is_generic', False)),
                     int(m.get('do_not_merge_globally', False)),
                     m.get('evidence_text', ''))
                )
                count += 1
            return count
    
    def find_by_chapter(self, chapter_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_entity_mention WHERE chapter_id = %s ORDER BY surface_text",
                (chapter_id,)
            )
            return cursor.fetchall()
    
    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_entity_mention WHERE book_id = %s ORDER BY chapter_id, surface_text",
                (book_id,)
            )
            return cursor.fetchall()
    
    def find_generic_mentions(self, book_id: int) -> List[dict]:
        """查找所有泛称提及"""
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_entity_mention WHERE book_id = %s AND is_generic = 1",
                (book_id,)
            )
            return cursor.fetchall()
    
    def delete_by_book(self, book_id: int):
        """删除一本书的所有 mention（重新提取时用）"""
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM novel_entity_mention WHERE book_id = %s", (book_id,))
