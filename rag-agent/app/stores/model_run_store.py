"""
Store module for novel_model_run table.
"""

from app.clients.mysql_client import MySQLClient


class ModelRunStore:
    def __init__(self, db: MySQLClient):
        self.db = db

    def insert(self, task_type: str, model_name: str, model_endpoint: str = "",
               book_source_id: int = 0, book_id: int = 0,
               chapter_id: int = 0, chunk_id: int = 0,
               agent_step_id: int = 0,
               prompt_version: str = "", schema_version: str = "", grammar_version: str = "",
               input_text: str = "", output_text: str = "",
               parse_status: str = "", status: str = "PENDING",
               error_type: str = "", error_message: str = "",
               retry_count: int = 0, duration_ms: int = 0) -> int:
        sql = """INSERT INTO novel_model_run
                 (agent_step_id, book_source_id, book_id, chapter_id, chunk_id,
                  task_type, model_name, model_endpoint,
                  prompt_version, schema_version, grammar_version,
                  input_text, output_text,
                  parse_status, status, error_type, error_message,
                  retry_count, duration_ms)
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s,
                         %s, %s, %s, %s, %s, %s)"""
        return self.db.insert(sql, (
            agent_step_id or None, book_source_id or None, book_id or None,
            chapter_id or None, chunk_id or None,
            task_type, model_name, model_endpoint,
            prompt_version, schema_version, grammar_version,
            input_text, output_text,
            parse_status, status, error_type, error_message,
            retry_count, duration_ms,
        ))

    def update_status(self, model_run_id: int, status: str, parse_status: str = "",
                      error_type: str = "", error_message: str = ""):
        updates = ["status = %s"]
        params = [status]
        if parse_status:
            updates.append("parse_status = %s")
            params.append(parse_status)
        if error_type:
            updates.append("error_type = %s")
            params.append(error_type)
        if error_message:
            updates.append("error_message = %s")
            params.append(error_message)
        params.append(model_run_id)
        sql = f"UPDATE novel_model_run SET {', '.join(updates)} WHERE id = %s"
        self.db.update(sql, tuple(params))

    def get_by_chunk(self, chunk_id: int) -> list:
        return self.db.fetch_all(
            "SELECT * FROM novel_model_run WHERE chunk_id = %s ORDER BY created_at DESC",
            (chunk_id,),
        )

    def get_by_id(self, model_run_id: int) -> dict:
        return self.db.fetch_one("SELECT * FROM novel_model_run WHERE id = %s", (model_run_id,))
