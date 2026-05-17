"""
Store module for novel_book_source table.
"""

import hashlib
from app.clients.mysql_client import MySQLClient


class BookSourceStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, title: str, author: str, raw_text: str,
               source_filename: str = "upload.txt", file_type: str = "txt") -> int:
        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        file_size = len(raw_text.encode("utf-8"))
        sql = """INSERT INTO novel_book_source
                 (title, author, source_filename, file_type, file_size, content_hash, raw_text, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, 'UPLOADED')"""
        return self.db.insert(sql, (title, author, source_filename, file_type, file_size, content_hash, raw_text))

    def get_by_id(self, book_source_id: int) -> dict:
        return self.db.fetch_one("SELECT * FROM novel_book_source WHERE id = %s", (book_source_id,))

    def update_status(self, book_source_id: int, status: str, error_message: str = ""):
        if error_message:
            self.db.update(
                "UPDATE novel_book_source SET status = %s, error_message = %s WHERE id = %s",
                (status, error_message, book_source_id),
            )
        else:
            self.db.update(
                "UPDATE novel_book_source SET status = %s WHERE id = %s",
                (status, book_source_id),
            )

    def list_all(self) -> list:
        return self.db.fetch_all(
            "SELECT id, title, author, source_filename, file_type, file_size, status, "
            "LENGTH(raw_text) as raw_text_length, created_at FROM novel_book_source ORDER BY id DESC"
        )
