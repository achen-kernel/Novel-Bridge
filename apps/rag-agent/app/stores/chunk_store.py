import hashlib

import pymysql


class ChunkStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert_chunk(
        self,
        book_id: int,
        chapter_id: int,
        chunk_index: int,
        content: str,
        start_offset: int,
        end_offset: int,
    ) -> int:
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_chunk
                     (book_id, chapter_id, chunk_index, content, start_offset, end_offset,
                      char_count, content_hash, status)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'CREATED')
                     ON DUPLICATE KEY UPDATE
                     content=VALUES(content), start_offset=VALUES(start_offset),
                     end_offset=VALUES(end_offset), char_count=VALUES(char_count),
                     content_hash=VALUES(content_hash), status='CREATED'"""
            cursor.execute(
                sql,
                (
                    book_id,
                    chapter_id,
                    chunk_index,
                    content,
                    start_offset,
                    end_offset,
                    len(content),
                    content_hash,
                ),
            )
            return cursor.lastrowid

    def find_by_chapter(self, chapter_id: int) -> list:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, content, chunk_index, start_offset, end_offset, char_count FROM novel_chunk WHERE chapter_id = %s ORDER BY chunk_index",
                (chapter_id,)
            )
            return cursor.fetchall()
