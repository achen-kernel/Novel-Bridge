"""Browse data demo for Book 6 - 西游记"""
import httpx

BASE = "http://127.0.0.1:18081"

print("=" * 60)
print("西游记数据浏览")
print("=" * 60)

print("\n=== 出场最多的角色 ===")
r = httpx.get(f"{BASE}/api/books/6/entities?min_mentions=30", timeout=10)
for e in r.json()[:8]:
    name = e["canonical_name"]
    count = e["mention_count"]
    aliases = e["aliases"]
    print(f"  {name:10s}  提及{count:3d}次  别名: {aliases}")

print("\n=== 主要关系 ===")
r = httpx.get(f"{BASE}/api/books/6/relations", timeout=10)
for rel in r.json()[:6]:
    a = rel["source_name"]
    b = rel["target_name"]
    t = rel["relation_type"]
    conf = rel["confidence"]
    print(f"  {a:8s} → {b:8s}  [{t}]  置信度={conf}")

print("\n=== 前5章 ===")
r = httpx.get(f"{BASE}/api/books/6/chapters", timeout=10)
for ch in r.json()[:5]:
    num = ch["chapter_number"]
    title = ch["title"]
    length = ch["raw_length"]
    print(f"  第{num}章  {title}  ({length}字)")

print("\n=== 全书概览 ===")
r = httpx.get(f"{BASE}/api/books/6", timeout=10)
d = r.json()
print(f"  作者: {d['author']}")
print(f"  章节: {d['chapter_count']}  |  Chunk: {d['chunk_count']}")
print(f"  Fact: {d['fact_count']}  |  实体: {d['entity_count']}")
print(f"  关系: {d['relation_count']}  |  别名决策: {d['alias_count']}")
