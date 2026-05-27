"""Add comprehensive eval test cases for all 5 books"""
import httpx

client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=10)

# Question bank: (book_id, question, difficulty)
questions = {
    6: [  # 西游记
        (6, '孙悟空的金箍棒是从哪里来的？', 'EASY'),
        (6, '猪八戒为什么被贬下凡间？', 'EASY'),
        (6, '唐僧有哪些徒弟？分别是谁？', 'MEDIUM'),
        (6, '孙悟空大闹天宫的原因是什么？', 'MEDIUM'),
        (6, '火焰山的火是怎么来的？', 'HARD'),
        (6, '唐僧西天取经经历了多少难？', 'MEDIUM'),
        (6, '沙僧在被贬之前是什么身份？', 'EASY'),
        (6, '观音菩萨用什么法术收服了孙悟空？', 'MEDIUM'),
    ],
    7: [  # 聊斋志异
        (7, '聂小倩是什么身份？', 'EASY'),
        (7, '画皮中的妖怪是如何害人的？', 'MEDIUM'),
        (7, '婴宁的性格特点是什么？', 'MEDIUM'),
        (7, '促织这篇故事讲述了什么？', 'MEDIUM'),
        (7, '崂山道士讲述了什么道理？', 'MEDIUM'),
        (7, '聊斋志异的作者是谁？', 'EASY'),
    ],
    8: [  # 搜神记
        (8, '搜神记主要记载了什么内容？', 'EASY'),
        (8, '干将莫邪的故事讲述了什么？', 'MEDIUM'),
        (8, '董永和七仙女的故事是怎样的？', 'MEDIUM'),
        (8, '搜神记的作者是谁？', 'EASY'),
        (8, '韩凭夫妇的故事讲述了什么？', 'MEDIUM'),
    ],
    9: [  # 山海经
        (9, '山海经中记载了哪些神兽？请举例', 'EASY'),
        (9, '精卫填海的故事是怎样的？', 'EASY'),
        (9, '夸父逐日的故事讲述了什么？', 'EASY'),
        (9, '山海经分为哪几部分？', 'MEDIUM'),
        (9, '刑天的故事是怎样的？', 'MEDIUM'),
    ],
    10: [  # 水浒传
        (10, '武松打虎的故事发生在哪里？', 'EASY'),
        (10, '林冲被逼上梁山的原因是什么？', 'MEDIUM'),
        (10, '宋江为什么能当上梁山首领？', 'HARD'),
        (10, '鲁智深倒拔垂杨柳的故事是怎样的？', 'MEDIUM'),
        (10, '梁山好汉一共有多少人？', 'EASY'),
        (10, '李逵的性格特点是什么？', 'MEDIUM'),
        (10, '杨志卖刀的故事是怎样的？', 'MEDIUM'),
        (10, '潘金莲和西门庆的故事是怎样的？', 'EASY'),
    ],
}

total = 0
for book_id, qlist in questions.items():
    for book_id_q, question, difficulty in qlist:
        payload = {
            'book_id': book_id_q,
            'question': question,
            'category': 'QA',
            'difficulty': difficulty,
            'expected_answer': '',
            'expected_entities': [],
        }
        # Use direct API - there might not be a POST /api/eval/cases endpoint
        # Let me check what endpoints exist
        print(f'Would add: [{difficulty}] Book {book_id}: {question}')
        total += 1

print(f'\nTotal question candidates: {total}')

# Check what endpoints exist for adding cases
r = client.get('/api/books')
if r.status_code == 200:
    print(f'Server reachable, {len(r.json())} books')
else:
    print(f'Server error: {r.status_code}')
