import json
from typing import List, Optional
import pymysql


class EventMentionStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert_batch(self, events: List[dict]) -> int:
        with self.conn.cursor() as cursor:
            count = 0
            for e in events:
                cursor.execute(
                    """INSERT INTO novel_event_mention
                       (book_id, chapter_id, chunk_id, event_type, summary,
                        participants_json, location, time_hint, event_trigger,
                        evidence_text, importance, confidence)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (e['book_id'], e['chapter_id'], e.get('chunk_id'),
                     e['event_type'], e.get('summary', ''),
                     json.dumps(e.get('participants', []), ensure_ascii=False),
                     e.get('location', ''), e.get('time_hint', ''),
                     e.get('event_trigger', ''), e.get('evidence_text', ''),
                     e.get('importance', 'MEDIUM'), e.get('confidence', 0.0)))
                count += 1
            return count

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_event_mention WHERE book_id = %s ORDER BY chapter_id",
                (book_id,))
            return cursor.fetchall()

    def find_by_chapter(self, chapter_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_event_mention WHERE chapter_id = %s ORDER BY importance",
                (chapter_id,))
            return cursor.fetchall()
