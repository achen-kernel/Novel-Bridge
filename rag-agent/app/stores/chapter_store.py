"""
Store module for novel_chapter table.
"""

from app.clients.mysql_client import MySQLClient


class ChapterStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, book_source_id: int, book_id: int, chapter_number: int,
               title: str, structure_type: str, start_offset: int, end_offset: int,
               raw_content: str = "", cleaned_content: str = "",
               char_count: int = 0, splitter_version: str = "") -> int:
        sql = """INSERT INTO novel_chapter
                 (book_source_id, book_id, chapter_number, structure_type, title,
                  start_offset, end_offset, raw_content, cleaned_content,
                  char_count, splitter_version, status)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREATED')"""
        return self.db.insert(sql, (
            book_source_id, book_id, chapter_number, structure_type, title,
            start_offset, end_offset, raw_content, cleaned_content,
            char_count, splitter_version,
        ))

    def get_by_book(self, book_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_chapter WHERE book_id = %s ORDER BY chapter_number",
            (book_id,),
        )

    def get_by_book_source(self, book_source_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_chapter WHERE book_source_id = %s ORDER BY chapter_number",
            (book_source_id,),
        )

    def count_by_book_source(self, book_source_id: int) -> int:
        row = self.db.fetch_one(
            "SELECT COUNT(*) as cnt FROM novel_chapter WHERE book_source_id = %s",
            (book_source_id,),
        )
        return row["cnt"] if row else 0
