import os, pymysql
c = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''), database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'))
with c.cursor() as cur:
    for bid in [6,7,8,9,10]:
        cur.execute('SELECT id, title, status FROM novel_book WHERE id=%s', (bid,))
        r = cur.fetchone()
        print(f'Book {r[0]} "{r[1]}": status={r[2]} (raw_text preserved)')
c.close()
