"""Debug entity/relation/event search on remote"""
import os, pymysql, json

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)

# Check entities related to 唐
with conn.cursor() as c:
    c.execute(
        "SELECT canonical_name, entity_type, description FROM novel_entity_profile "
        "WHERE book_id = 6 AND canonical_name LIKE %s LIMIT 20",
        ('%唐%',)
    )
    rows = c.fetchall()
    print(f'Entities containing 唐: {len(rows)}')
    for r in rows:
        print(f'  [{r["canonical_name"]}] type={r["entity_type"]}')

print()

# Check if exact 唐僧 exists
with conn.cursor() as c:
    c.execute(
        "SELECT canonical_name FROM novel_entity_profile "
        "WHERE book_id = 6 AND canonical_name = %s",
        ('唐僧',)
    )
    rows = c.fetchall()
    print(f'Exact match "唐僧": {len(rows)} rows')

# Check relation_fact
with conn.cursor() as c:
    c.execute(
        "SELECT source_entity_name, relation_type, target_entity_name FROM novel_relation_fact "
        "WHERE book_id = 6 AND source_entity_name LIKE %s LIMIT 10",
        ('%僧%',)
    )
    rows = c.fetchall()
    print(f'Relations with 僧: {len(rows)}')
    for r in rows:
        print(f'  [{r["source_entity_name"]}] --[{r["relation_type"]}]--> [{r["target_entity_name"]}]')

# Check event_fact for 唐僧
with conn.cursor() as c:
    c.execute(
        "SELECT id, description FROM novel_event_fact "
        "WHERE book_id = 6 AND description IS NOT NULL AND description != '' AND description LIKE %s LIMIT 3",
        ('%唐僧%',)
    )
    rows = c.fetchall()
    print(f'Events with 唐僧: {len(rows)}')
    for r in rows:
        print(f'  #{r["id"]}: {r["description"][:100]}')

conn.close()
