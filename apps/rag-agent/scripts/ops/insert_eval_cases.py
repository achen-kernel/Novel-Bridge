"""Insert eval test cases for all 5 books"""
import sys
sys.path.insert(0, '/home/wk/novelbridge/apps/rag-agent')

import os, pymysql
from app.stores.eval_store import EvalStore

conn = pymysql.connect(
    host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', 13306)), user='novel_bridge', password=os.environ.get('MYSQL_PASSWORD', ''),
    database=os.environ.get('MYSQL_DATABASE', 'novel_bridge'), charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor
)
store = EvalStore(conn)

# Question bank: (book_id, question, difficulty)
questions = [
    # 西游记 (Book 6)
    (6, '孙悟空的金箍棒是从哪里来的？', 'EASY'),
    (6, '猪八戒为什么被贬下凡间？', 'EASY'),
    (6, '唐僧有哪些徒弟？分别是谁？', 'MEDIUM'),
    (6, '孙悟空大闹天宫的原因是什么？', 'MEDIUM'),
    (6, '火焰山的火是怎么来的？', 'HARD'),
    (6, '唐僧西天取经经历了多少难？', 'MEDIUM'),
    (6, '沙僧在被贬之前是什么身份？', 'EASY'),
    (6, '观音菩萨用什么法术收服了孙悟空？', 'MEDIUM'),
    # 聊斋志异 (Book 7)
    (7, '聂小倩是什么身份？', 'EASY'),
    (7, '画皮中的妖怪是如何害人的？', 'MEDIUM'),
    (7, '婴宁的性格特点是什么？', 'MEDIUM'),
    (7, '促织这篇故事讲述了什么？', 'MEDIUM'),
    (7, '崂山道士讲述了什么道理？', 'MEDIUM'),
    (7, '聊斋志异的作者是谁？', 'EASY'),
    # 搜神记 (Book 8)
    (8, '搜神记主要记载了什么内容？', 'EASY'),
    (8, '干将莫邪的故事讲述了什么？', 'MEDIUM'),
    (8, '董永和七仙女的故事是怎样的？', 'MEDIUM'),
    (8, '搜神记的作者是谁？', 'EASY'),
    (8, '韩凭夫妇的故事讲述了什么？', 'MEDIUM'),
    # 山海经 (Book 9)
    (9, '山海经中记载了哪些神兽？请举例', 'EASY'),
    (9, '精卫填海的故事是怎样的？', 'EASY'),
    (9, '夸父逐日的故事讲述了什么？', 'EASY'),
    (9, '山海经分为哪几部分？', 'MEDIUM'),
    (9, '刑天的故事是怎样的？', 'MEDIUM'),
    # 水浒传 (Book 10)
    (10, '武松打虎的故事发生在哪里？', 'EASY'),
    (10, '林冲被逼上梁山的原因是什么？', 'MEDIUM'),
    (10, '宋江为什么能当上梁山首领？', 'HARD'),
    (10, '鲁智深倒拔垂杨柳的故事是怎样的？', 'MEDIUM'),
    (10, '梁山好汉一共有多少人？', 'EASY'),
    (10, '李逵的性格特点是什么？', 'MEDIUM'),
    (10, '杨志卖刀的故事是怎样的？', 'MEDIUM'),
    (10, '潘金莲和西门庆的故事是怎样的？', 'EASY'),
]

count = 0
for book_id, question, difficulty in questions:
    # Check if it already exists
    with conn.cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM novel_eval_case WHERE book_id = %s AND question = %s",
                  (book_id, question))
        row = c.fetchone()
        if row and row['cnt'] > 0:
            print(f'SKIP (exists): [{difficulty}] Book {book_id}: {question}')
            continue

    store.insert_case(
        book_id=book_id,
        question=question,
        category='QA',
        difficulty=difficulty,
    )
    count += 1
    print(f'ADDED: [{difficulty}] Book {book_id}: {question}')

conn.commit()
print(f'\nInserted {count} new cases')
conn.close()
