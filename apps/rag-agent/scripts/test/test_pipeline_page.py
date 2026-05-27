"""Test pipeline API and page"""
import httpx
c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=15)
r = c.get('/api/pipeline/6/status')
d = r.json()
print('Pipeline status:')
print(f'  Book: {d["book_title"]} ({d["book_status"]})')
for ph in d['phases']:
    print(f'  {ph["phase"]} {ph["name"]}: {ph["status"]}')
r = c.get('/pipeline/6')
print(f'Pipeline page: status={r.status_code}, length={len(r.text)}')
