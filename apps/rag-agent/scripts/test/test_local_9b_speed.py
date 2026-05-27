"""Test local 9B response time for a single question"""
import httpx, time
c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=300)
t0 = time.time()
r = c.post('/api/qa/ask', json={
    'book_id': 6, 'question': '孙悟空的金箍棒是从哪里来的？',
    'session_id': 0, 'use_deepseek': False
})
elapsed = time.time() - t0
d = r.json()
ans = d.get('answer', '')[:150]
cits = len(d.get('citations', []))
print(f'Time: {elapsed:.1f}s')
print(f'Answer: {ans}')
print(f'Citations: {cits}')
