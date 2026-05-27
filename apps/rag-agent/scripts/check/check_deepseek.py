"""Check DeepSeek config and test QA"""
import httpx, json

BASE = "http://127.0.0.1:18081"

# Check config
r = httpx.get(f"{BASE}/health/llm", timeout=5)
print(f"LLM health: {r.json()}")

# Test QA with DeepSeek
qa_req = {
    "session_id": 0,
    "book_id": 6,
    "question": "孙悟空大闹天宫时，和哪些神仙打过？",
    "use_deepseek": True
}
r = httpx.post(f"{BASE}/api/qa/ask", json=qa_req, timeout=120)
result = r.json()
print(f"\nAnswer: {str(result.get('answer',''))[:500]}")
print(f"\nCitations ({len(result.get('citations',[]))}):")
for c in result.get('citations', [])[:3]:
    print(f"  [{c['source_type']}] id={c['source_id']} score={c['relevance_score']}: {c['excerpt'][:100]}")
