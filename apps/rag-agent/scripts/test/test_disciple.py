import httpx
client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=60)

q = '唐僧有哪些徒弟？分别是谁？'
r = client.post('/api/qa/ask', json={'book_id': 6, 'question': q, 'session_id': 0, 'use_deepseek': True})
ans = r.json()
print(f'Q: {q}')
print(f'A: {ans.get("answer","")[:500]}')
print(f'Citations: {len(ans.get("citations",[]))}')
if ans.get('citations'):
    for c in ans['citations'][:3]:
        print(f'  cite: {c.get("excerpt","")[:80]}')
