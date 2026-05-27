import json
from typing import List, Optional
import pymysql


class RelationMentionStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert_batch(self, mentions: List[dict]) -> int:
        with self.conn.cursor() as cursor:
            count = 0
            for m in mentions:
                cursor.execute(
                    """INSERT INTO novel_relation_mention 
                       (book_id, chapter_id, chunk_id, source_entity_name, target_entity_name,
                        relation_type, relation_family, relation_polarity, direction,
                        evidence_text, relation_trigger, confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (m['book_id'], m['chapter_id'], m.get('chunk_id'),
                     m['source_entity_name'], m['target_entity_name'],
                     m['relation_type'], m.get('relation_family', 'OTHER'),
                     m.get('relation_polarity', 'UNKNOWN'), m.get('direction', 'UNKNOWN'),
                     m.get('evidence_text', ''), m.get('relation_trigger', ''),
                     m.get('confidence', 0.0))
                )
                count += 1
            return count

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_relation_mention WHERE book_id = %s ORDER BY chapter_id",
                (book_id,))
            return cursor.fetchall()

    def find_by_entity(self, book_id: int, entity_name: str) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """SELECT * FROM novel_relation_mention 
                   WHERE book_id = %s AND (source_entity_name = %s OR target_entity_name = %s)
                   ORDER BY chapter_id""",
                (book_id, entity_name, entity_name))
            return cursor.fetchall()
