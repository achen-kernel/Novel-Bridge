"""
Plot Stage 存储层。
"""
import json
from typing import List, Optional

import pymysql


class PlotStageStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def insert(self, book_id: int, stage_index: int, stage_name: str,
               summary: str = "", start_chapter_id: int = None,
               end_chapter_id: int = None,
               key_entities: list = None) -> int:
        with self.conn.cursor() as cursor:
            key_entities_json = json.dumps(key_entities or [], ensure_ascii=False)
            cursor.execute(
                """INSERT INTO novel_plot_stage
                   (book_id, stage_index, stage_name, summary,
                    start_chapter_id, end_chapter_id, key_entities_json)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                   stage_name = VALUES(stage_name),
                   summary = VALUES(summary),
                   updated_at = NOW()""",
                (book_id, stage_index, stage_name, summary,
                 start_chapter_id, end_chapter_id, key_entities_json))
            return cursor.lastrowid

    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_plot_stage WHERE book_id = %s ORDER BY stage_index",
                (book_id,))
            return cursor.fetchall()

    def delete_by_book(self, book_id: int):
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM novel_plot_stage WHERE book_id = %s", (book_id,))
