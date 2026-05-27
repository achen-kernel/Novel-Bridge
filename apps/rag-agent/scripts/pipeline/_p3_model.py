"""Trigger P3 with use_model=True for a book."""
import asyncio, httpx, sys, time

book_id = int(sys.argv[1])
API = "http://127.0.0.1:18079"

async def main():
    async with httpx.AsyncClient(timeout=None) as c:
        print(f"P3 book {book_id} with model starting...")
        t0 = time.time()
        r = await c.post(f"{API}/api/books/{book_id}/extract", json={"use_model": True})
        elapsed = time.time() - t0
        j = r.json()
        print(f"P3 book {book_id} DONE in {elapsed:.0f}s: {j.get('status')} chapters={j.get('chapters_processed')}/{j.get('success_count')}")
        if j.get('error'):
            print(f"  ERROR: {j['error']}")

asyncio.run(main())
