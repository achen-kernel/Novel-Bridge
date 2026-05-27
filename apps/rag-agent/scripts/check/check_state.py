"""Check DB state"""
import sys; sys.path.insert(0,'.')
from app.clients.mysql_client import MysqlClient
conn = MysqlClient().connect()

with conn.cursor() as c:
    c.execute("SHOW TABLES")
    print("Tables:", [list(r.values())[0] for r in c.fetchall()])

with conn.cursor() as c:
    c.execute("SELECT book_id, COUNT(*) as cnt FROM novel_chapter_fact GROUP BY book_id ORDER BY book_id")
    print("\nFacts per book:")
    for r in c.fetchall():
        print(f"  Book {r['book_id']}: {r['cnt']} facts")

with conn.cursor() as c:
    c.execute("SELECT id, title, chapter_count FROM novel_book ORDER BY id")
    print("\nBooks:")
    for r in c.fetchall():
        print(f"  Book {r['id']}: {r['title']} ({r['chapter_count']} chaps)")

conn.close()
