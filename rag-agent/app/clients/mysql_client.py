"""
NovelBridge — MySQL client for rag-agent.

Provides async-safe connection pooling via PyMySQL.
All credentials from environment variables.
"""

import os
import pymysql
from pymysql.cursors import DictCursor

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "13306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "12345678")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "novel_bridge")


def get_connection():
    """Return a new PyMySQL connection (blocking, use in runners, not in hot-path handlers)."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


class MySQLClient:
    """Thin wrapper around PyMySQL for store modules."""

    def __init__(self):
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or not self._conn.open:
            self._conn = get_connection()
        return self._conn

    def execute(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur

    def fetch_one(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()

    def fetch_all(self, sql: str, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

    def insert(self, sql: str, params=None) -> int:
        with self.conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.lastrowid

    def update(self, sql: str, params=None) -> int:
        with self.conn.cursor() as cur:
            affected = cur.execute(sql, params or ())
            return affected

    def close(self):
        if self._conn and self._conn.open:
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()
