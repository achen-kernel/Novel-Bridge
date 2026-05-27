import json
from datetime import datetime
from typing import Optional

import pymysql


class ModelRunStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn

    def get_run(self, run_id: int) -> Optional[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_agent_run WHERE id = %s", (run_id,)
            )
            return cursor.fetchone()

    def create_run(self, run_type: str, book_id: int, input_data: dict = None) -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_agent_run 
                     (run_type, book_id, status, input_json, started_at)
                     VALUES (%s, %s, 'RUNNING', %s, %s)"""
            cursor.execute(sql, (
                run_type,
                book_id,
                json.dumps(input_data, ensure_ascii=False) if input_data else None,
                datetime.now()
            ))
            return cursor.lastrowid

    def update_run_status(
        self,
        run_id: int,
        status: str,
        output: dict = None,
        error_type: str = None,
        error_message: str = None,
    ):
        with self.conn.cursor() as cursor:
            sql = "UPDATE novel_agent_run SET status = %s"
            params = [status]
            if output:
                sql += ", output_json = %s"
                params.append(json.dumps(output, ensure_ascii=False))
            if error_type:
                sql += ", error_type = %s"
                params.append(error_type)
            if error_message:
                sql += ", error_message = %s"
                params.append(error_message)
            if status in ("SUCCESS", "FAILED", "CANCELED"):
                sql += ", completed_at = %s"
                params.append(datetime.now())
            sql += " WHERE id = %s"
            params.append(run_id)
            cursor.execute(sql, params)

    def create_step(
        self, run_id: int, step_type: str, step_order: int, input_data: dict = None
    ) -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_agent_step
                     (agent_run_id, step_type, step_order, status, input_json, started_at)
                     VALUES (%s, %s, %s, 'RUNNING', %s, %s)"""
            cursor.execute(
                sql,
                (
                    run_id,
                    step_type,
                    step_order,
                    json.dumps(input_data, ensure_ascii=False) if input_data else None,
                    datetime.now(),
                ),
            )
            return cursor.lastrowid

    def update_step_status(
        self,
        step_id: int,
        status: str,
        output: dict = None,
        error_type: str = None,
        error_message: str = None,
    ):
        with self.conn.cursor() as cursor:
            sql = "UPDATE novel_agent_step SET status = %s"
            params = [status]
            if output:
                sql += ", output_json = %s"
                params.append(json.dumps(output, ensure_ascii=False))
            if error_type:
                sql += ", error_type = %s"
                params.append(error_type)
            if error_message:
                sql += ", error_message = %s"
                params.append(error_message)
            if status in ("SUCCESS", "FAILED"):
                sql += ", completed_at = %s"
                params.append(datetime.now())
            sql += " WHERE id = %s"
            params.append(step_id)
            cursor.execute(sql, params)
