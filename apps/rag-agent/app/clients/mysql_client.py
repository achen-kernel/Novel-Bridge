import pymysql
from typing import Optional


class MysqlClient:
    def __init__(self):
        self.connection: Optional[pymysql.Connection] = None

    def connect(self) -> pymysql.Connection:
        if self.connection is None or not self._is_connected():
            from app.config import settings
            self.connection = pymysql.connect(
                host=settings.mysql_host,
                port=settings.mysql_port,
                user=settings.mysql_user,
                password=settings.mysql_password,
                database=settings.mysql_database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=True
            )
        return self.connection

    def _is_connected(self) -> bool:
        try:
            self.connection.ping(reconnect=True)
            return True
        except Exception:
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    async def health_check(self) -> dict:
        try:
            conn = self.connect()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                return {"status": "ok", "detail": "MySQL connected"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}
