"""Run P4 for Books 8,9,10"""
import httpx, time
c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=600)
for bid in [8, 9, 10]:
    t0 = time.time()
    r = c.post(f'/api/books/{bid}/govern')
    data = r.json()
    print(f'Book {bid}: {data.get("profiles",0)} profiles, {data.get("status","?")} | {time.time()-t0:.0f}s')
