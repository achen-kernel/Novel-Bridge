"""Run quality workflow per book to see stats"""
import pymysql, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.quality.stages.entity_name_normalizer import EntityNameNormalizer
from app.quality.stages.relation_deduper import RelationDeduper

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

print('--- Entity Name Normalizer (per book) ---')
normalizer = EntityNameNormalizer(conn)
for bid in [6, 7, 8, 9, 10]:
    r = normalizer.run(book_id=bid, dry_run=True)
    s = r['stats']
    print(f'  Book {bid}: {s["scanned"]} mismatches from {s["alias_map_size"]} alias entries')

print()
print('--- Relation Deduper (per book) ---')
deduper = RelationDeduper(conn)
for bid in [6, 7, 8, 9, 10]:
    r = deduper.run(book_id=bid, dry_run=True)
    s = r['stats']
    print(f'  Book {bid}: {s["total_groups"]} dup groups, {s["rows_to_merge"]} rows to merge')

conn.close()
print('Done')

