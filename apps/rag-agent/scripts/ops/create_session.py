"""Create a chat session for testing QA"""
import os, pymysql
conn = pymysql.connect(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user="novel_bridge",
                       password=os.environ.get('MYSQL_PASSWORD', ''), db=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset="utf8mb4")
c = conn.cursor()
c.execute("INSERT IGNORE INTO novel_chat_session (id, book_id, title) VALUES (1, 6, '西游记测试')")
conn.commit()
print("Session 1 created")
conn.close()
