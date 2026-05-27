"""Check table schemas for browse endpoints"""
import os, pymysql
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
                       password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")
c = conn.cursor()
for t in ["novel_event_fact", "novel_relation_fact", "novel_entity_profile"]:
    print(f"=== {t} ===")
    c.execute(f"DESCRIBE {t}")
    for r in c.fetchall():
        print(f"  {r[0]}: {r[1]}")
    print()
conn.close()
