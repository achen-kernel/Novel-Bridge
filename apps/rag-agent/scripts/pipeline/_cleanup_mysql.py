"""Cleanup MySQL derived data for books 6-10 before re-run."""
import os, pymysql

c = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'))
with c.cursor() as cur:
    book_ids = '6,7,8,9,10'
    tables = [
        'novel_plot_stage', 'novel_event_fact', 'novel_event_mention',
        'novel_relation_fact', 'novel_relation_mention', 'novel_alias_decision',
        'novel_entity_profile', 'novel_entity_mention', 'novel_model_call',
        'novel_chapter_fact', 'novel_chunk', 'novel_chapter'
    ]
    for t in tables:
        sql = 'DELETE FROM {} WHERE book_id IN ({})'.format(t, book_ids)
        cur.execute(sql)
        print(f'{t}: deleted {cur.rowcount} rows')
    cur.execute("UPDATE novel_book SET status='IMPORTED', chapter_count=0, chunk_count=0 WHERE id IN ({})".format(book_ids))
    print(f'books reset: {cur.rowcount} rows')
c.commit()
c.close()
print('DONE: MySQL cleanup complete')
