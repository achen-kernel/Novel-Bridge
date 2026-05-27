"""Fix Book 8 counters"""
import os, pymysql
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
                       password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")
c = conn.cursor()
c.execute("UPDATE novel_book SET chapter_count=35, chunk_count=35 WHERE id=8")
conn.commit()
print("Fixed Book 8: chapter_count=35, chunk_count=35")
conn.close()
