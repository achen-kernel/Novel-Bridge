"""
Run the quality improvement workflow in dry-run mode first.
If --apply is passed, actually execute.
"""
import os
import sys
import pymysql

sys.path.insert(0, '/home/wk/novelbridge/apps/rag-agent')

from app.quality.stages.entity_name_normalizer import EntityNameNormalizer
from app.quality.stages.relation_deduper import RelationDeduper
from app.quality.stages.event_summarizer import EventSummarizer

DRY_RUN = '--apply' not in sys.argv

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=False,
)

mode = 'DRY-RUN' if DRY_RUN else 'APPLY'
print(f'=== Quality Improvement Workflow ({mode}) ===')
print()

# Stage 1: Entity Name Normalizer
print('--- Stage 1: Entity Name Normalizer ---')
normalizer = EntityNameNormalizer(conn)
r1 = normalizer.run(dry_run=DRY_RUN)
print(f'  Stats: {r1["stats"]}')
print(f'  Message: {r1["message"]}')
if r1.get('change_preview'):
    print(f'  Preview ({len(r1["change_preview"])} shown):')
    for c in r1['change_preview'][:5]:
        print(f'    id={c["id"]} book={c["book_id"]} field={c["field"]}: {c["old_value"]} → {c["new_value"]}')
print()

# Stage 2: Relation Deduper
print('--- Stage 2: Relation Deduper ---')
deduper = RelationDeduper(conn)
r2 = deduper.run(dry_run=DRY_RUN)
print(f'  Stats: {r2["stats"]}')
print(f'  Message: {r2["message"]}')
if r2.get('change_preview'):
    print(f'  Preview ({len(r2["change_preview"])} shown):')
    for c in r2['change_preview'][:5]:
        print(f'    merge {c["merge_id"]} → keep {c["keep_id"]} ({c["entity_a"]} --[{c["relation_type"]}]--> {c["entity_b"]})')
print()

# Stage 3: Event Summarizer
print('--- Stage 3: Event Summarizer ---')
summarizer = EventSummarizer(conn)
r3 = summarizer.run(dry_run=DRY_RUN)
print(f'  Stats: {r3["stats"]}')
print(f'  Message: {r3["message"]}')
print()

conn.close()
print(f'=== Done ({mode}) ===')
