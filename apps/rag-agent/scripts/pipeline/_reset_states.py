"""Reset stale pipeline states for books 6-9."""
import urllib.request, json

for bid in [6, 7, 8, 9]:
    try:
        req = urllib.request.Request(
            f'http://127.0.0.1:18079/api/v2/books/{bid}/pipeline-state/reset?stage=0',
            method='POST'
        )
        r = urllib.request.urlopen(req, timeout=10)
        data = json.loads(r.read())
        print(f"Book {bid}: {data['status']}")
    except Exception as e:
        print(f"Book {bid} error: {e}")
