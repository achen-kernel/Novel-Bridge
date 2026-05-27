"""Debug: check if pipeline page & API actually work."""
import urllib.request, json

# Test API
r = urllib.request.urlopen('http://127.0.0.1:18079/api/v2/pipeline/books')
data = json.loads(r.read())
books = data.get('books', [])
print(f'API OK: {len(books)} books returned')

# Test page serves HTML
r2 = urllib.request.urlopen('http://127.0.0.1:18079/pipeline')
html = r2.read().decode('utf-8')
print(f'Page OK: {len(html)} chars served')
print(f'  Has loadPipeline: {chr(10) not in html}')
print(f'  Has refreshStatus count: {html.count(chr(114)+chr(101)+chr(102)+chr(114)+chr(101)+chr(115)+chr(104)+chr(83)+chr(116)+chr(97)+chr(116)+chr(117)+chr(115))}')
# Count braces in script
import re
m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if m:
    js = m.group(1)
    ob = js.count('{')
    cb = js.count('}')
    print(f'JS: {len(js)} chars, braces open={ob} close={cb}')
    # Check last function is valid
    last_fn = js[js.rfind('function'):] if 'function' in js else 'none'
    print(f'  Last function: {last_fn[:60]}...')
    
print('All checks passed' if books and html else 'SOMETHING WRONG')
