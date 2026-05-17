"""
Store module for novel_entity_candidate table.
"""

import json
from app.clients.mysql_client import MySQLClient


class CandidateStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, book_source_id: int, book_id: int, chapter_id: int,
               chunk_id: int, model_run_id: int,
               name: str, entity_type: str, evidence_text: str,
               confidence: float, uncertain: bool = False,
               aliases: list = None, description: str = "") -> int:
        aliases_json = json.dumps(aliases or [], ensure_ascii=False)
        sql = """INSERT INTO novel_entity_candidate
                 (book_source_id, book_id, chapter_id, chunk_id, model_run_id,
                  name, entity_type, aliases_json, description,
                  evidence_text, confidence, uncertain, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING_REVIEW')"""
        return self.db.insert(sql, (
            book_source_id, book_id, chapter_id, chunk_id, model_run_id,
            name, entity_type, aliases_json, description,
            evidence_text, confidence, int(uncertain),
        ))

    def get_by_chunk(self, chunk_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_entity_candidate WHERE chunk_id = %s ORDER BY created_at DESC",
            (chunk_id,),
        )

    def get_by_book_source(self, book_source_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_entity_candidate WHERE book_source_id = %s ORDER BY created_at DESC",
            (book_source_id,),
        )

    def get_pending(self, book_source_id: int = None, limit: int = 50) -> list:
        if book_source_id:
            return self.db.fetch_all(
                "SELECT * FROM novel_entity_candidate WHERE status = 'PENDING_REVIEW' AND book_source_id = %s ORDER BY created_at LIMIT %s",
                (book_source_id, limit),
            )
        return self.db.fetch_all(
            "SELECT * FROM novel_entity_candidate WHERE status = 'PENDING_REVIEW' ORDER BY created_at LIMIT %s",
            (limit,),
        )

    def get_by_id(self, candidate_id: int) -> dict:
        return self.db.fetch_one(
            "SELECT * FROM novel_entity_candidate WHERE id = %s",
            (candidate_id,),
        )

    def update_status(self, candidate_id: int, status: str):
        self.db.update(
            "UPDATE novel_entity_candidate SET status = %s WHERE id = %s",
            (status, candidate_id),
        )

    def update_fields(self, candidate_id: int, **kwargs):
        sets = []
        params = []
        for k, v in kwargs.items():
            sets.append(f"{k} = %s")
            params.append(v)
        params.append(candidate_id)
        self.db.update(
            f"UPDATE novel_entity_candidate SET {', '.join(sets)} WHERE id = %s",
            tuple(params),
        )

    def count_pending(self, book_source_id: int = None) -> int:
        if book_source_id:
            row = self.db.fetch_one(
                "SELECT COUNT(*) as cnt FROM novel_entity_candidate WHERE status = 'PENDING_REVIEW' AND book_source_id = %s",
                (book_source_id,),
            )
        else:
            row = self.db.fetch_one(
                "SELECT COUNT(*) as cnt FROM novel_entity_candidate WHERE status = 'PENDING_REVIEW'",
            )
        return row["cnt"] if row else 0
