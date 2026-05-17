"""
Store module for novel_chunk table.
"""

import hashlib
import uuid
from app.clients.mysql_client import MySQLClient


class ChunkStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, book_source_id: int, book_id: int, chapter_id: int,
               chunk_index: int, text: str,
               start_offset: int, end_offset: int,
               char_count: int = 0, token_count: int = 0,
               chunk_strategy: str = "", chunk_version: str = "") -> int:
        chunk_uid = str(uuid.uuid4())
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        sql = """INSERT INTO novel_chunk
                 (book_source_id, book_id, chapter_id, chunk_index, chunk_uid,
                  content, start_offset, end_offset,
                  char_count, token_count, content_hash,
                  chunk_strategy, chunk_version, vector_status, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'NOT_INDEXED', 'CREATED')"""
        return self.db.insert(sql, (
            book_source_id, book_id, chapter_id, chunk_index, chunk_uid,
            text, start_offset, end_offset,
            char_count, token_count, content_hash,
            chunk_strategy, chunk_version,
        ))

    def get_by_chapter(self, chapter_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_chunk WHERE chapter_id = %s ORDER BY chunk_index",
            (chapter_id,),
        )

    def get_by_book_source(self, book_source_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_chunk WHERE book_source_id = %s ORDER BY chapter_id, chunk_index",
            (book_source_id,),
        )

    def get_by_id(self, chunk_id: int) -> dict:
        return self.db.fetch_one("SELECT * FROM novel_chunk WHERE id = %s", (chunk_id,))

    def get_unprocessed(self, book_source_id: int, limit: int = 10) -> list:
        """Get chunks that haven't been processed for entity extraction."""
        sql = """SELECT c.* FROM novel_chunk c
                 LEFT JOIN novel_model_run mr ON mr.chunk_id = c.id AND mr.task_type = 'ENTITY_EXTRACT'
                 WHERE c.book_source_id = %s AND mr.id IS NULL
                 ORDER BY c.chapter_id, c.chunk_index
                 LIMIT %s"""
        return self.db.fetch_all(sql, (book_source_id, limit))

    def count_by_book_source(self, book_source_id: int) -> int:
        row = self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_source_id = %s",
            (book_source_id,),
        )
        return row["cnt"] if row else 0

    def update_vector_status(self, chunk_id: int, status: str, embedding_id: str = ""):
        if embedding_id:
            self.db.update(
                "UPDATE novel_chunk SET vector_status = %s, embedding_id = %s WHERE id = %s",
                (status, embedding_id, chunk_id),
            )
        else:
            self.db.update(
                "UPDATE novel_chunk SET vector_status = %s WHERE id = %s",
                (status, chunk_id),
            )
