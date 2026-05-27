import urllib.request, re
html = urllib.request.urlopen('http://127.0.0.1:18079/pipeline').read().decode('utf-8')
m = re.search(r'<script>(.*?)</script>', html, re.DOTALL)
if m:
    js = m.group(1)
    lines = js.split('\n')
    print(f'Script: {len(js)} chars, {len(lines)} lines')
    # Check for top-level await (await at start of line, outside any function)
    in_function = 0
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith('async function') or s.startswith('function ') or s == '{':
            if s.startswith('async function') or s.startswith('function '):
                in_function += 1
        if s == '}':
            in_function = max(0, in_function - 1)
        if s.startswith('await ') and in_function == 0:
            print(f'LINE {i+1}: TOP-LEVEL AWAIT: {s[:80]}')
    
    # Show last lines
    print(f'Last 5 lines:')
    for line in lines[-5:]:
        print(f'  {line.rstrip()[:100]}')
