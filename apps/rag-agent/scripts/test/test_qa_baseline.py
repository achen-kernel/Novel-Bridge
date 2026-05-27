"""Test current QA baseline with 5 questions"""
import httpx, json, time

client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=60)

tests = [
    # Book 6 - 西游记
    (6, '孙悟空的金箍棒是从哪里来的？'),
    (6, '猪八戒为什么被贬下凡间？'),
    (6, '唐僧有哪些徒弟？分别是谁？'),
    # Book 10 - 水浒传
    (10, '武松打虎的故事发生在哪里？'),
    # Book 7 - 聊斋
    (7, '聂小倩是什么身份？'),
]

for book_id, question in tests:
    start = time.time()
    payload = {'book_id': book_id, 'question': question, 'session_id': 0, 'use_deepseek': True}
    try:
        r = client.post('/api/qa/ask', json=payload)
        elapsed = time.time() - start
        ans = r.json()
        a = ans.get('answer', '')[:200]
        c = ans.get('citations', [])
        print(f'[{elapsed:.1f}s] [{book_id}] Q: {question}')
        print(f'  A: {a}')
        print(f'  Citations: {len(c)}')
        print()
    except Exception as e:
        print(f'ERROR for {book_id}: {e}')
        print()
