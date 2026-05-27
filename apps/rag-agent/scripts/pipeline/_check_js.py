import re
with open('D:/Novel-Bridge/pipeline_test.html','r',encoding='utf-8') as f:
    html = f.read()
m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if m:
    js = m.group(1)
    print(f'JS length: {len(js)} chars')
    open_braces = js.count('{')
    close_braces = js.count('}')
    print(f'Braces: open={open_braces}, close={close_braces}, diff={open_braces-close_braces}')
    sq = len(re.findall(r"'(?<!\\)(.*?)'", js))
    print(f'Rough single quotes: even pairs expected')
    # Check last 100 chars
    print(f'Last 100 chars: {repr(js[-100:])}')
else:
    print('No script tag')
