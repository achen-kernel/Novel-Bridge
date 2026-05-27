"""Quick view: what was built"""
import os, pymysql
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
                       password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")
c = conn.cursor()

print("=== Books ===")
c.execute("SELECT id, title, status, chapter_count, chunk_count FROM novel_book ORDER BY id")
for r in c.fetchall():
    print(f"  [{r[0]}] {r[1]}  status={r[2]}  ch={r[3]}  chunks={r[4]}")

print("\n=== Processing Stats ===")
for bid in [6, 7, 9, 10]:
    print(f"  Book {bid}:")
    for t in ["novel_chapter_fact","novel_entity_mention","novel_entity_profile",
               "novel_alias_decision","novel_relation_mention","novel_event_mention"]:
        c.execute(f"SELECT COUNT(*) FROM {t} WHERE book_id={bid}")
        print(f"    {t}: {c.fetchone()[0]}")

print("\n=== Training Samples ===")
c.execute("SELECT book_id, COUNT(*) FROM novel_training_sample GROUP BY book_id")
for r in c.fetchall():
    print(f"  Book {r[0]}: {r[1]}")

conn.close()

print("\n=== Qdrant (ssh to remote) ===")
print("  ssh wk@192.168.3.50 ... python _check_qdrant.py")

print("\n=== Training Data Files (remote) ===")
print("  ssh wk@192.168.3.50 'ls -la /home/wk/novelbridge/apps/rag-agent/training/data/'")
