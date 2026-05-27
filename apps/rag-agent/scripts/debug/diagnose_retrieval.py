"""Diagnose why retrieval returns no results for QA"""
import httpx, json

client = httpx.Client(base_url='http://127.0.0.1:18081', timeout=30)

questions = [
    (6, '孙悟空的金箍棒是从哪里来的？'),
    (6, '猪八戒为什么被贬下凡间？'),
    (6, '唐僧有哪些徒弟？分别是谁？'),
    (10, '武松打虎的故事发生在哪里？'),
    (7, '聂小倩是什么身份？'),
]

# First check what books are available
r = client.get('/api/books')
print("=== Books ===")
for b in r.json():
    print(f"  [{b['id']}] {b['title']} — {b.get('chapter_count',0)} ch, {b.get('chunk_count',0)} chunks")

# Check entity table for aliases
print("\n=== Sample entities ===")
for bid in [6, 10, 7]:
    r = client.get(f'/api/books/{bid}/entities', params={'limit': 5})
    data = r.json()
    ents = data if isinstance(data, list) else data.get('entities', [])
    print(f"  Book {bid}: {len(ents)} entities (showing first):")
    for e in ents[:3]:
        print(f"    [{e.get('id')}] {e.get('name')} — aliases={e.get('alias_count',0)}")

# Check Qdrant stats for chunks
print("\n=== Qdrant chunk count check ===")
for bid in [6, 7, 10]:
    # Check MySQL chunk count
    pass  # can't query MySQL directly from here

# Direct keyword search: count chunks containing "金箍棒"
print("\n=== Trying raw search via browse API ===")
# Check chapters that might contain "金箍棒"
r = client.get(f'/api/books/6/chapters')
chapters = r.json()
print(f"Book 6 has {len(chapters)} chapters")

# Let me also check: how many chunks does book 6 have?
# Use a simple test: search for chunks
from urllib.parse import quote
test_q = quote('金箍棒')
r = client.get(f'/api/books/6/chapters?limit=3')
print(f"\nBook 6 chapter sample: {r.text[:200]}")
