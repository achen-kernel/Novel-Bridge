"""Check remaining Book 10 mismatches"""
import pymysql, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.quality.stages.entity_name_normalizer import EntityNameNormalizer

conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor)

normalizer = EntityNameNormalizer(conn)
r = normalizer.run(book_id=10, dry_run=True)

# Show all remaining mismatches
print(f'Remaining: {len(r["changes"])}')
seen = set()
for c in r['changes'][:30]:
    key = f'{c["old_value"]}->{c["new_value"]}'
    if key not in seen:
        seen.add(key)
        print(f'  {c["old_value"]} -> {c["new_value"]}')

# Check if these are alias-able
alias_map = normalizer._build_alias_map(10)
print(f'\nAlias map size: {len(alias_map)}')

# Check a few specific ones
for test_name in ['鏉庨€?, '楂樹繀', '姝︽澗', '瀹嬫睙', '鐕曢潚', '鏋楀啿']:
    found = alias_map.get(test_name, 'NOT FOUND')
    print(f'  "{test_name}" -> "{found}"')

conn.close()

