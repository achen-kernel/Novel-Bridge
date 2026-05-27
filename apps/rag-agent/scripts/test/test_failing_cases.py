"""Test the 9 previously failing QA cases"""
import httpx

client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=60)

failures = [
    (6, '火焰山的火是怎么来的？'),
    (6, '唐僧西天取经经历了多少难？'),
    (6, '沙僧在被贬之前是什么身份？'),
    (6, '观音菩萨用什么法术收服了孙悟空？'),
    (7, '聊斋志异中哪个故事最著名？'),
    (7, '画皮中的妖怪是如何害人的？'),
    (10, '鲁智深倒拔垂杨柳的故事是怎样的？'),
    (10, '梁山好汉一共有多少人？'),
]

for book_id, question in failures:
    payload = {'book_id': book_id, 'question': question, 'session_id': 0, 'use_deepseek': True}
    r = client.post('/api/qa/ask', json=payload)
    ans = r.json()
    answer = ans.get('answer', '')[:120]
    cits = len(ans.get('citations', []))
    verdict = '✅' if cits > 0 else '❌'
    print(f'{verdict} [{book_id}] {question}')
    print(f'  A: {answer}')
    print(f'  Cits: {cits}')
    print()
