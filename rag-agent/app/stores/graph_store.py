"""
Store module for entity_profile and review_record tables.
"""

import json
from app.clients.mysql_client import MySQLClient


class EntityProfileStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, book_id: int, entity_name: str, entity_type: str,
               description: str = "", significance: str = "MINOR",
               aliases: list = None,
               first_chapter_id: int = 0, last_chapter_id: int = 0) -> int:
        aliases_json = json.dumps(aliases or [], ensure_ascii=False)
        sql = """INSERT INTO novel_entity_profile
                 (book_id, entity_name, entity_type, aliases, description,
                  significance, first_chapter_id, last_chapter_id, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'APPROVED')"""
        return self.db.insert(sql, (
            book_id, entity_name, entity_type, aliases_json, description,
            significance,
            first_chapter_id or None, last_chapter_id or None,
        ))

    def get_by_book(self, book_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_entity_profile WHERE book_id = %s ORDER BY significance, entity_name",
            (book_id,),
        )

    def get_by_name(self, book_id: int, entity_name: str) -> dict:
        return self.db.fetch_one(
            "SELECT * FROM novel_entity_profile WHERE book_id = %s AND entity_name = %s",
            (book_id, entity_name),
        )


class ReviewRecordStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, candidate_id: int, review_action: str,
               old_values: dict = None, new_values: dict = None,
               reviewer: str = "", comment: str = "") -> int:
        sql = """INSERT INTO novel_review_record
                 (candidate_id, review_action, old_values, new_values, reviewer, comment)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        return self.db.insert(sql, (
            candidate_id, review_action,
            json.dumps(old_values) if old_values else None,
            json.dumps(new_values) if new_values else None,
            reviewer, comment,
        ))

    def get_by_candidate(self, candidate_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_review_record WHERE candidate_id = %s ORDER BY reviewed_at",
            (candidate_id,),
        )
