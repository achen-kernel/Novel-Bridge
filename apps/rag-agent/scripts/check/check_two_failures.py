"""Debug two failing questions"""
import json
import os
import pymysql

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

# Q3: 唐僧有哪些徒弟？分别是谁？ (Book 6)
print("="*60)
print("Q: 唐僧有哪些徒弟？分别是谁？ (Book 6)")
print("="*60)

# Check entity alias expansion
with conn.cursor() as cur:
    cur.execute(
        "SELECT canonical_name, aliases_json FROM novel_entity_profile "
        "WHERE book_id = 6 AND status = 'ACTIVE' AND canonical_name LIKE '%唐僧%'"
    )
    for row in cur.fetchall():
        print(f"  Entity: {row['canonical_name']}, aliases: {row.get('aliases_json','')[:100]}")

# Check chunks with 唐僧 and 徒弟
with conn.cursor() as cur:
    cur.execute(
        "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 6 AND content LIKE '%唐僧%'"
    )
    cnt = cur.fetchone()['cnt']
    print(f"  Chunks containing '唐僧': {cnt}")
    
    cur.execute(
        "SELECT id, content FROM novel_chunk WHERE book_id = 6 AND content LIKE '%唐僧%' LIMIT 1"
    )
    row = cur.fetchone()
    if row:
        print(f"  Sample chunk #{row['id']}: {row['content'][:200]}")

    cur.execute(
        "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 6 AND content LIKE '%徒弟%'"
    )
    cnt = cur.fetchone()['cnt']
    print(f"  Chunks containing '徒弟': {cnt}")
    
    # Check specific: disciples mentioned together
    for disciple in ['孙悟空', '猪八戒', '沙僧']:
        cur.execute(
            "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 6 AND content LIKE %s AND content LIKE %s",
            ('%唐僧%', f'%{disciple}%')
        )
        cnt = cur.fetchone()['cnt']
        print(f"  Chunks with '唐僧' + '{disciple}': {cnt}")

# Q4: 武松打虎的故事发生在哪里？(Book 10)
print()
print("="*60)
print("Q: 武松打虎的故事发生在哪里？(Book 10)")
print("="*60)

with conn.cursor() as cur:
    cur.execute(
        "SELECT canonical_name, aliases_json FROM novel_entity_profile "
        "WHERE book_id = 10 AND status = 'ACTIVE' AND canonical_name LIKE '%武松%'"
    )
    for row in cur.fetchall():
        print(f"  Entity: {row['canonical_name']}, aliases: {row.get('aliases_json','')[:100]}")

with conn.cursor() as cur:
    cur.execute(
        "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 10 AND content LIKE '%武松%'"
    )
    cnt = cur.fetchone()['cnt']
    print(f"  Chunks containing '武松': {cnt}")
    
    cur.execute(
        "SELECT id, content FROM novel_chunk WHERE book_id = 10 AND content LIKE '%武松%' LIMIT 1"
    )
    row = cur.fetchone()
    if row:
        content = row['content'][:300]
        print(f"  Sample chunk #{row['id']}: {content}")
    
    cur.execute(
        "SELECT COUNT(*) as cnt FROM novel_chunk WHERE book_id = 10 AND content LIKE '%打虎%'"
    )
    cnt = cur.fetchone()['cnt']
    print(f"  Chunks containing '打虎': {cnt}")
    
    if cnt > 0:
        cur.execute(
            "SELECT id, content FROM novel_chunk WHERE book_id = 10 AND content LIKE '%打虎%' LIMIT 1"
        )
        row = cur.fetchone()
        print(f"  Chunk: {row['content'][:300]}")
    
    # Check chapter fact content for these questions
    cur.execute(
        "SELECT summary FROM novel_chapter_fact WHERE book_id = 10 AND summary LIKE '%武松%' LIMIT 1"
    )
    row = cur.fetchone()
    if row:
        print(f"  Fact summary: {row['summary'][:200]}")

conn.close()
