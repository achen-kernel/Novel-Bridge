"""
Run P3-P8 for all 5 books using rule-based extraction (fast).
P4-P8 after each P3 completes.
"""
import asyncio, httpx, sys, time

API = "http://127.0.0.1:18079"
BOOKS = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}

async def post(url, json_data=None, label="", timeout=3600):
    async with httpx.AsyncClient(timeout=timeout) as c:
        t0 = time.time()
        r = await c.post(url, json=json_data or {})
        elapsed = time.time() - t0
        result = r.json()
        status = result.get("status", "?")
        error = result.get("error", "")
        detail = f"status={status}"
        if "chapters_processed" in result:
            detail += f" chapters={result.get('chapters_processed')}/{result.get('success_count')}"
        if "chunks_indexed" in result:
            detail += f" chunks={result.get('chunks_indexed')} facts={result.get('facts_indexed')}"
        if "mentions" in result:
            detail += f" mentions={result.get('mentions')} profiles={result.get('profiles')}"
        print(f"  [{label}] {elapsed:.0f}s {detail}" + (f" ERROR={error[:120]}" if error else ""))
        return result

async def main():
    print(f"Pipeline P3-P8 rule-based (use_model=False)")
    print(f"{'='*50}")

    for bid, bname in BOOKS.items():
        print(f"\n{'─'*40}")
        print(f"  {bname}({bid})")
        print(f"{'─'*40}")

        # P3: extract (rule-based, fast)
        print(f"  P3: extract...")
        await post(f"{API}/api/books/{bid}/extract", {"use_model": False}, f"P3-{bid}")

        # P4: govern
        print(f"  P4: govern...")
        await post(f"{API}/api/books/{bid}/govern", {}, f"P4-{bid}")

        # P5: narrative
        print(f"  P5: narrative...")
        await post(f"{API}/api/books/{bid}/narrative", {}, f"P5-{bid}")

        # P6: index (reindex=True -> clear + rebuild)
        print(f"  P6: index...")
        await post(f"{API}/api/books/{bid}/index", {"reindex": True}, f"P6-{bid}")

        # P7: graph projection
        print(f"  P7: graph...")
        await post(f"{API}/api/books/{bid}/graph/project", {}, f"P7-{bid}")

        # P8: export
        print(f"  P8: export...")
        await post(f"{API}/api/eval/export/chapter-facts?book_id={bid}&min_review=PENDING", {}, f"P8-{bid}", 120)

        print(f"  ✅ {bname}({bid}) 完成")

    print(f"\n{'='*50}")
    print(f"  全部 5 本完成！")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
