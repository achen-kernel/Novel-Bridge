"""Re-export training data for all books with unique timestamps"""
import httpx, time

for bid in [6, 7, 8, 9, 10]:
    time.sleep(1.01)  # unique timestamp per file
    r = httpx.post(
        f"http://127.0.0.1:18081/api/eval/export/chapter-facts?book_id={bid}&min_review=PENDING",
        timeout=30
    )
    d = r.json()
    print(f"Book {bid}: {d}")
