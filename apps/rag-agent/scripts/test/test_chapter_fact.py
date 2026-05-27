"""Test chapter fact endpoint - 西游记 Chapter 1"""
import httpx

BASE = "http://127.0.0.1:18081"

# Get chapters to find the first chapter ID
r = httpx.get(f"{BASE}/api/books/6/chapters", timeout=10)
chapters = r.json()
first_ch = chapters[0]
print(f"First chapter: id={first_ch['id']}, {first_ch['title']}")

# Get chapter fact
r = httpx.get(f"{BASE}/api/chapters/{first_ch['id']}/fact", timeout=10)
d = r.json()

print(f"\n=== Chapter {d['chapter_number']}: {d['chapter_title']} ===")
print(f"Summary: {d['summary'][:300] if d['summary'] else '(none)'}")
print(f"Evidence: {d['evidence_status']} | Review: {d['review_status']}")

chars = d.get("characters", [])
print(f"\nCharacters ({len(chars)}):")
for c in chars[:8]:
    name = c.get("display_name") or c.get("name") or "?"
    etype = c.get("entity_type", "")
    evid = str(c.get("evidence_text", ""))[:80]
    print(f"  {name:12s} ({etype:12s})  evid: {evid}")

rels = d.get("relations", [])
print(f"\nRelations ({len(rels)}):")
for r in rels[:6]:
    src = r.get("source", "?")
    tgt = r.get("target", "?")
    rtype = r.get("relation_type", "")
    print(f"  {src:8s} -> {tgt:8s}  [{rtype}]")

evts = d.get("events", [])
print(f"\nEvents ({len(evts)}):")
for e in evts[:4]:
    print(f"  {e.get('summary','')[:100]}")
