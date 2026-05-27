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

    def new_connection(self) -> pymysql.Connection:
        """创建并返回一个全新的独立连接（线程安全，用于线程池任务）。"""
        from app.config import settings
        import logging
        log = logging.getLogger(__name__)
        log.info("new_connection: host=%s port=%s user=%s db=%s",
                 settings.mysql_host, settings.mysql_port, settings.mysql_user, settings.mysql_database)
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

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
