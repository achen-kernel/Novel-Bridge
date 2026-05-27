"""Trigger P3 extraction for a single book and wait for completion."""
import asyncio
import sys
import httpx

book_id = int(sys.argv[1]) if len(sys.argv) > 1 else 6
book_names = {6: "西游记", 7: "聊斋志异", 8: "搜神记", 9: "山海经", 10: "水浒传"}
book_name = book_names.get(book_id, f"Book {book_id}")

async def main():
    async with httpx.AsyncClient(timeout=None) as c:
        print(f"[P3] {book_name}({book_id}) starting...")
        t0 = asyncio.get_event_loop().time()
        r = await c.post(
            f"http://127.0.0.1:18079/api/books/{book_id}/extract",
            json={"use_model": True}
        )
        elapsed = asyncio.get_event_loop().time() - t0
        result = r.json()
        status = result.get("status", "?")
        run_id = result.get("run_id", 0)
        chapters = result.get("chapters_processed", 0)
        success = result.get("success_count", 0)
        error = result.get("error", "")
        print(f"[P3] {book_name}({book_id}) DONE in {elapsed:.0f}s")
        print(f"  Status: {status}")
        print(f"  Run ID: {run_id}")
        print(f"  Chapters: {chapters}, Success: {success}")
        if error:
            print(f"  ERROR: {error}")

if __name__ == "__main__":
    asyncio.run(main())
