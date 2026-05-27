"""Clean Book 6 leftover data"""
import sys; sys.path.insert(0,'.')
from app.clients.mysql_client import MysqlClient
conn = MysqlClient().connect()

with conn.cursor() as c:
    c.execute("DELETE FROM novel_chapter_fact WHERE book_id=6")
    conn.commit()
    print(f"Cleaned Book 6 facts")

with conn.cursor() as c:
    c.execute("SELECT COUNT(*) as cnt FROM novel_chapter_fact WHERE book_id=6")
    print(f"Book 6 facts now: {c.fetchone()['cnt']}")

conn.close()
print("Done")
