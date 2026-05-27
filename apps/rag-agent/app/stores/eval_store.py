import json
from datetime import datetime
from typing import List, Optional
import pymysql


class EvalStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    # ---- Eval Cases ----

    def insert_case(self, book_id: int, question: str, expected_answer: str = "",
                    expected_entities: List[str] = None,
                    category: str = "QA", difficulty: str = "MEDIUM") -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_eval_case
                   (book_id, question, expected_answer, expected_entities_json, category, difficulty)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (book_id, question, expected_answer,
                 json.dumps(expected_entities or [], ensure_ascii=False),
                 category, difficulty))
            return cursor.lastrowid

    def find_cases(self, book_id: int = None, category: str = None) -> List[dict]:
        with self.conn.cursor() as cursor:
            sql = "SELECT * FROM novel_eval_case WHERE status = 'ACTIVE'"
            params = []
            if book_id:
                sql += " AND book_id = %s"
                params.append(book_id)
            if category:
                sql += " AND category = %s"
                params.append(category)
            sql += " ORDER BY created_at"
            cursor.execute(sql, params)
            return cursor.fetchall()

    # ---- Eval Runs ----

    def create_run(self, run_type: str) -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO novel_eval_run (run_type, status, started_at) VALUES (%s, 'RUNNING', %s)",
                (run_type, datetime.now()))
            return cursor.lastrowid

    def update_run(self, run_id: int, status: str, summary: dict = None):
        with self.conn.cursor() as cursor:
            sql = "UPDATE novel_eval_run SET status = %s"
            params = [status]
            if summary:
                sql += ", summary_json = %s"
                params.append(json.dumps(summary, ensure_ascii=False))
            if status in ('SUCCESS', 'FAILED'):
                sql += ", completed_at = %s"
                params.append(datetime.now())
            sql += " WHERE id = %s"
            params.append(run_id)
            cursor.execute(sql, params)

    def find_runs(self) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM novel_eval_run ORDER BY created_at DESC")
            return cursor.fetchall()

    def find_run(self, run_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM novel_eval_run WHERE id = %s", (run_id,))
            return cursor.fetchone()

    # ---- Eval Results ----

    def insert_result(self, run_id: int, case_id: int, question: str,
                      actual_answer: str = "", citations: List[dict] = None,
                      scores: dict = None, error_type: str = "") -> int:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO novel_eval_result
                   (run_id, case_id, question, actual_answer, citations_json, scores_json, error_type, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (run_id, case_id, question, actual_answer,
                 json.dumps(citations or [], ensure_ascii=False) if citations else None,
                 json.dumps(scores or {}, ensure_ascii=False) if scores else None,
                 error_type, 'done' if not error_type else 'failed'))
            return cursor.lastrowid

    def find_results(self, run_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_eval_result WHERE run_id = %s ORDER BY id",
                (run_id,))
            return cursor.fetchall()
