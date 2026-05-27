"""Test retrieval verbosely for the two failing questions"""
import httpx, json

client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=30)

# Test failing Qs directly - see what retrieval returns
# For now, let's re-test the full pipeline 
tests = [
    (6, '唐僧有哪些徒弟？分别是谁？'),
    (10, '武松打虎的故事发生在哪里？'),
]

for book_id, question in tests:
    print(f"{'='*60}")
    print(f"Q [{book_id}]: {question}")
    print('='*60)
    payload = {'book_id': book_id, 'question': question, 'session_id': 0, 'use_deepseek': True}
    r = client.post('/api/qa/ask', json=payload)
    ans = r.json()
    print(f"Answer: {ans.get('answer','')[:300]}")
    print(f"Citations: {len(ans.get('citations',[]))}")
    if ans.get('citations'):
        for c in ans['citations'][:3]:
            print(f"  cite: type={c.get('source_type')} id={c.get('source_id')} excerpt={c.get('excerpt','')[:80]}")
    print()
