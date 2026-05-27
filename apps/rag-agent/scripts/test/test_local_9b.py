"""Test local 9B QA"""
import httpx, time
c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=300)
# Test 1: simple question
t0 = time.time()
r = c.post('/api/qa/ask', json={
    'book_id': 6,
    'question': '孙悟空的金箍棒是从哪里来的？',
    'session_id': 0,
    'use_deepseek': False
})
d = r.json()
ans = d.get('answer', '')[:200]
cits = len(d.get('citations', []))
print(f'[local9B] Q1: 金箍棒')
print(f'  Time: {time.time()-t0:.1f}s')
print(f'  Ans: {ans}')
print(f'  Cits: {cits}')
print()

# Test 2: with DeepSeek for comparison
t0 = time.time()
r = c.post('/api/qa/ask', json={
    'book_id': 6,
    'question': '孙悟空的金箍棒是从哪里来的？',
    'session_id': 0,
    'use_deepseek': True
})
d = r.json()
ans = d.get('answer', '')[:200]
cits = len(d.get('citations', []))
print(f'[DeepSeek] Q1: 金箍棒')
print(f'  Time: {time.time()-t0:.1f}s')
print(f'  Ans: {ans}')
print(f'  Cits: {cits}')
