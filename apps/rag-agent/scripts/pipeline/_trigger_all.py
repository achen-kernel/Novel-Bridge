"""
Trigger full pipeline P1-P8 for all 5 books.
Runs P1+P2 (fast) first, then P3-P8 one book at a time.
P3 takes ~2h per book - monitor progress via uvicorn logs.
"""
import asyncio
import httpx
import sys
import time

API = "http://127.0.0.1:18079"
BOOKS = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}

async def post(url, json_data=None, label="", timeout=43200):
    async with httpx.AsyncClient(timeout=timeout) as c:
        t0 = time.time()
        r = await c.post(url, json=json_data or {})
        elapsed = time.time() - t0
        result = r.json()
        status = result.get("status", "?")
        error = result.get("error", "")
        print(f"  [{label}] {elapsed:.0f}s status={status}" + (f" error={error[:100]}" if error else ""))
        return result

async def main():
    print(f"NovelBridge 全量管线 P1-P8 启动")
    print(f"API: {API}")
    print()

    current_task = None
    for bid, bname in BOOKS.items():
        print(f"\n{'='*50}")
        print(f"  {bname}({bid})")
        print(f"{'='*50}")

        # P1: split chapters + chunk
        print(f"  --- P1: split+chunk ---")
        await post(f"{API}/api/books/{bid}/process", {}, label=f"P1-{bid}")

        # P2: prior hint (DeepSeek)
        print(f"  --- P2: prior hint ---")
        await post(f"{API}/api/books/{bid}/prior-hint", {}, label=f"P2-{bid}")

        # P3: extract (LONG - ~2h)
        print(f"  --- P3: extract (use_model=True) [预计 1-2h] ---")
        await post(f"{API}/api/books/{bid}/extract", {"use_model": True}, label=f"P3-{bid}")

        # P4: govern
        print(f"  --- P4: govern ---")
        await post(f"{API}/api/books/{bid}/govern", {}, label=f"P4-{bid}")

        # P5: narrative
        print(f"  --- P5: narrative ---")
        await post(f"{API}/api/books/{bid}/narrative", {}, label=f"P5-{bid}")

        # P6: index (reindex=True -> clear + rebuild)
        print(f"  --- P6: index ---")
        await post(f"{API}/api/books/{bid}/index", {"reindex": True}, label=f"P6-{bid}")

        # P7: graph projection
        print(f"  --- P7: graph ---")
        await post(f"{API}/api/books/{bid}/graph/project", {}, label=f"P7-{bid}")

        # P8: export
        print(f"  --- P8: export ---")
        await post(f"{API}/api/eval/export/chapter-facts?book_id={bid}&min_review=PENDING", {}, label=f"P8-{bid}", timeout=120)

        print(f"  ✅ {bname}({bid}) 完成")

    print(f"\n{'='*50}")
    print(f"  🎉 全部 5 本完成！")
    print(f"{'='*50}")

if __name__ == "__main__":
    asyncio.run(main())
