"""Check database state for all books"""
import sys; sys.path.insert(0,'.')
from app.clients.mysql_client import MysqlClient
from app.config import settings

conn = MysqlClient().connect()
cursor = conn.cursor()

print("=== Books ===")
cursor.execute("SELECT id, title, status, chapter_count FROM novel_book ORDER BY id")
for r in cursor.fetchall():
    print(f'  Book {r["id"]}: {r["title"]} | status={r["status"]} | chapters={r["chapter_count"]}')

print("\n=== Facts per book ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_chapter_fact GROUP BY book_id ORDER BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} facts')

print("\n=== Entities ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_entity GROUP BY book_id ORDER BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} entities')

print("\n=== Relations ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_relationship GROUP BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} relations')

print("\n=== Events ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_event GROUP BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} events')

print("\n=== Training Samples ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_training_sample GROUP BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} samples')

print("\n=== Chapters per book ===")
cursor.execute("SELECT book_id, COUNT(*) as c FROM novel_chapter GROUP BY book_id ORDER BY book_id")
for r in cursor.fetchall():
    print(f'  Book {r["book_id"]}: {r["c"]} chapters')

cursor.close()
conn.close()
print("\nDone.")
