"""Check Book 8 state"""
import os, pymysql
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
                       password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")
c = conn.cursor()

print("=== Book 8 ===")
c.execute("SELECT id, title, status, chapter_count, chunk_count, LENGTH(raw_text) FROM novel_book WHERE id=8")
r = c.fetchone()
print(f"  id={r[0]}, title={r[1]}, status={r[2]}, ch={r[3]}, ck={r[4]}, raw_len={r[5]}")

print("\n=== Chapters ===")
c.execute("SELECT COUNT(*) FROM novel_chapter WHERE book_id=8")
print(f"  {c.fetchone()[0]}")

print("\n=== Data counts ===")
for t in ["novel_chapter_fact","novel_chunk","novel_entity_mention","novel_entity_profile",
          "novel_alias_decision","novel_relation_mention","novel_event_mention","novel_training_sample"]:
    c.execute(f"SELECT COUNT(*) FROM {t} WHERE book_id=8")
    print(f"  {t}: {c.fetchone()[0]}")

print("\n=== Agent runs ===")
c.execute("SELECT id, run_type, status, output_json FROM novel_agent_run WHERE book_id=8 ORDER BY id")
for r in c.fetchall():
    out = str(r[3])[:200] if r[3] else "NULL"
    print(f"  run {r[0]}: type={r[1]}, status={r[2]}, output={out}")

conn.close()
