"""Test QA endpoint with DeepSeek"""
import httpx, json, sys

BASE = "http://127.0.0.1:18081"

# Test 1: LLM health
r = httpx.get(f"{BASE}/health/llm", timeout=5)
print(f"LLM health: {r.json()}")

# Test 2: QA with DeepSeek
qa_req = {
    "session_id": 0,
    "book_id": 10,
    "question": "武松打虎的故事是怎样的？",
    "use_deepseek": True
}
print(f"\nSending QA request: {json.dumps(qa_req, ensure_ascii=False)[:200]}")
try:
    r = httpx.post(f"{BASE}/api/qa/ask", json=qa_req, timeout=120)
    print(f"Status: {r.status_code}")
    print(f"Headers: {dict(r.headers)}")
    if r.status_code == 200:
        result = r.json()
        answer = result.get("answer", "")
        print(f"\nAnswer ({len(answer)} chars):")
        print(answer[:800])
        print(f"\nCitations: {len(result.get('citations', []))}")
        for c in result.get("citations", [])[:3]:
            print(f"  [{c['source_type']}] id={c['source_id']} score={c['relevance_score']}")
            print(f"    {c['excerpt'][:150]}")
    else:
        print(f"Response body: {r.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")
