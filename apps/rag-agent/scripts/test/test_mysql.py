import sys
sys.path.insert(0, '/home/wk/novelbridge/apps/rag-agent')
from app.config import settings
print('Password:', repr(settings.mysql_password))
print('Host:', settings.mysql_host, 'Port:', settings.mysql_port)

import pymysql
try:
    conn = pymysql.connect(
        host=settings.mysql_host, port=settings.mysql_port,
        user=settings.mysql_user, password=settings.mysql_password,
        database=settings.mysql_database, cursorclass=pymysql.cursors.DictCursor
    )
    with conn.cursor() as c:
        c.execute('SELECT COUNT(*) as c FROM novel_book')
        print('MySQL OK, books:', c.fetchone()['c'])
    conn.close()
except Exception as e:
    print('MySQL FAILED:', e)
