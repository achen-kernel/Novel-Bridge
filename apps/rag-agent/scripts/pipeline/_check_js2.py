import re
with open('D:/Novel-Bridge/apps/rag-agent/app/api/frontend.py','r',encoding='utf-8') as f:
    c = f.read()
m = re.search(r'<script>(.*?)</script>', c, re.DOTALL)
if m:
    js = m.group(1)
    lines = js.split('\n')
    in_async = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('async function'):
            in_async += 1
        elif s == '}':
            in_async = max(0, in_async - 1)
        if s.startswith('await') and in_async == 0 and '//' not in s:
            print(f'LINE {i+1}: TOP-LEVEL AWAIT: {s[:80]}')
    
    print(f'loadPipeline defined: {"async function loadPipeline" in js}')
    print(f'loadPipeline call: {"loadPipeline();" in js}')
    print(f'refreshStatus count: {js.count("async function refreshStatus")}')
    print(f'esc defined: {"function esc(" in js}')
    
    # Check line 70 area
    print(f'\nLines 65-75:')
    for l in lines[64:75]:
        print(f'  {l.rstrip()[:120]}')
