"""
Alias Decision 存储层。
"""
import json
from typing import List, Optional

import pymysql


class AliasDecisionStore:
    def __init__(self, conn: pymysql.Connection):
        self.conn = conn
    
    def insert_decision(self, book_id: int, entity_a_name: str, entity_b_name: str,
                        decision: str, confidence: float = 0.0,
                        reason: str = "", risk_types: List[str] = None,
                        reviewer: str = "RULE") -> int:
        with self.conn.cursor() as cursor:
            sql = """INSERT INTO novel_alias_decision 
                     (book_id, entity_a_name, entity_b_name, decision, confidence,
                      reason, risk_types_json, reviewer)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            risk_json = json.dumps(risk_types or [], ensure_ascii=False)
            cursor.execute(sql, (book_id, entity_a_name, entity_b_name, decision,
                                confidence, reason, risk_json, reviewer))
            return cursor.lastrowid
    
    def find_by_book(self, book_id: int) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_alias_decision WHERE book_id = %s ORDER BY created_at DESC",
                (book_id,)
            )
            return cursor.fetchall()
    
    def find_decisions_by_type(self, decision: str) -> List[dict]:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM novel_alias_decision WHERE decision = %s ORDER BY created_at DESC",
                (decision,)
            )
            return cursor.fetchall()
    
    def delete_by_book(self, book_id: int):
        with self.conn.cursor() as cursor:
            cursor.execute("DELETE FROM novel_alias_decision WHERE book_id = %s", (book_id,))
