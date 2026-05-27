"""Test new browse/search/entity endpoints"""
import httpx

c = httpx.Client(base_url='http://127.0.0.1:18081', timeout=15)

# Search
r = c.get('/api/search?q=孙悟空&limit=5')
data = r.json()
print(f'Search: status={r.status_code}, total={data.get("total",0)}, results={len(data.get("results",[]))}')

# Entity detail
r = c.get('/api/entities/7441')
if r.status_code == 200:
    e = r.json()
    print(f'Entity detail: name={e["canonical_name"]}, relations={len(e.get("relations",[]))}')
else:
    print(f'Entity detail: status={r.status_code}')

# Search page HTML
r = c.get('/search?q=孙悟空')
print(f'Search page: status={r.status_code}, length={len(r.text)}')

# QA page
r = c.get('/qa')
print(f'QA page: status={r.status_code}, length={len(r.text)}')

# Book page
r = c.get('/browse/book/6?page=0')
print(f'Book page: status={r.status_code}, length={len(r.text)}')

print('All OK')
