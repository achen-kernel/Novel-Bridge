import httpx
c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=60)
r = c.post('/api/qa/ask', json={'book_id': 6, 'question': '火焰山的火是怎么来的？', 'session_id': 0, 'use_deepseek': True})
d = r.json()
ans = d.get('answer','')
print(f'Answer: {ans[:300]}')
print(f'Citations: {len(d.get("citations",[]))}')
for cit in d.get('citations',[])[:2]:
    print(f'  type={cit.get("source_type","?")} excerpt={cit.get("excerpt","")[:80]}')
