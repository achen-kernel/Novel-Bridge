"""Apply quality improvement: entity name sync then relation dedup"""
import pymysql, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.quality.stages.entity_name_normalizer import EntityNameNormalizer
from app.quality.stages.relation_deduper import RelationDeduper

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

total_normalized = 0
total_merged = 0

books = [6, 7, 8, 9, 10]

print('=== Stage 1: Entity Name Normalizer ===')
normalizer = EntityNameNormalizer(conn)
for bid in books:
    r = normalizer.run(book_id=bid, dry_run=False)
    n = r['stats']['updated']
    total_normalized += n
    print(f'  Book {bid}: normalized {n} names')
print(f'  Total: {total_normalized} names normalized')
print()

print('=== Stage 2: Relation Deduper ===')
deduper = RelationDeduper(conn)
for bid in books:
    r = deduper.run(book_id=bid, dry_run=False)
    m = r['stats'].get('rows_actually_merged', 0) or r['stats'].get('rows_to_merge', 0)
    total_merged += m
    print(f'  Book {bid}: merged {m} duplicate rows')
print(f'  Total: {total_merged} rows merged')
print()

conn.close()
print(f'Done. Normalized {total_normalized} names, merged {total_merged} duplicates.')

