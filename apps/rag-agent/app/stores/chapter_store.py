import pymysql


class ChapterStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert_chapter(
        self,
        book_id: int,
        chapter_number: int,
        title: str,
        content: str,
        start_offset: int,
        end_offset: int,
        split_strategy: str,
        split_confidence: float,
    ) -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_chapter
                     (book_id, chapter_number, title, raw_content, start_offset, end_offset,
                      char_count, split_strategy, split_confidence, status)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'CREATED')
                     ON DUPLICATE KEY UPDATE
                     title=VALUES(title), raw_content=VALUES(raw_content),
                     start_offset=VALUES(start_offset), end_offset=VALUES(end_offset),
                     char_count=VALUES(char_count), split_strategy=VALUES(split_strategy),
                     split_confidence=VALUES(split_confidence), status='CREATED'"""
            cursor.execute(
                sql,
                (
                    book_id,
                    chapter_number,
                    title,
                    content,
                    start_offset,
                    end_offset,
                    len(content),
                    split_strategy,
                    split_confidence,
                ),
            )
            return cursor.lastrowid

    def get_chapters_by_book(self, book_id: int) -> list:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, chapter_number, title, raw_content, char_count FROM novel_chapter "
                "WHERE book_id = %s ORDER BY chapter_number",
                (book_id,),
            )
            return cursor.fetchall()
