"""List tables and Book 6 facts"""
import sys; sys.path.insert(0,'.')
from app.clients.mysql_client import MysqlClient
conn = MysqlClient().connect()
cursor = conn.cursor()

cursor.execute("SHOW TABLES")
print("Tables:")
for r in cursor.fetchall():
    print(f"  {list(r.values())[0]}")

cursor.execute("SELECT COUNT(*) as c FROM novel_chapter_fact WHERE book_id=6")
print(f"\nBook 6 facts: {cursor.fetchone()['c']}")

cursor.execute("SELECT COUNT(*) as c FROM novel_chapter WHERE book_id=6")
print(f"Book 6 chapters: {cursor.fetchone()['c']}")

cursor.execute("SELECT status FROM novel_book WHERE id=6")
print(f"Book 6 status: {cursor.fetchone()['status']}")

cursor.close(); conn.close()
