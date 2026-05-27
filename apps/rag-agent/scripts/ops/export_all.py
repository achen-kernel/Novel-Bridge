"""
Export training data for all books with fixed naming (no overwrite).
Each book gets its own file.
"""
import httpx

BASE = "http://127.0.0.1:18081"

for bid in [6, 7, 8, 9, 10]:
    r = httpx.post(
        f"{BASE}/api/eval/export/chapter-facts?book_id={bid}&min_review=PENDING",
        timeout=30
    )
    d = r.json()
    print(f"Book {bid}: {d['samples']} samples -> {d['file']}")
