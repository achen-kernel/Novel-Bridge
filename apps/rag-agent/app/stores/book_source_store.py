from typing import Optional

import pymysql


class BookSourceStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def get_book_raw_text(self, book_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, title, author, raw_text, source_encoding, char_count, prior_hint_json "
                "FROM novel_book WHERE id = %s",
                (book_id,),
            )
            return cursor.fetchone()

    def update_book_status(
        self,
        book_id: int,
        status: str,
        chapter_count: int = 0,
        chunk_count: int = 0,
        error_message: str = None,
    ):
        with self.conn.cursor() as cursor:
            sql = (
                "UPDATE novel_book SET status = %s, chapter_count = %s, chunk_count = %s"
            )
            params = [status, chapter_count, chunk_count]
            if error_message:
                sql += ", error_message = %s"
                params.append(error_message)
            sql += " WHERE id = %s"
            params.append(book_id)
            cursor.execute(sql, params)
