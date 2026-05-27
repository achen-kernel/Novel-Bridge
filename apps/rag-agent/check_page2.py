"""Check rendered page for common issues."""
with open('D:\\Novel-Bridge\\temp_page.html', encoding='utf-8') as f:
    html = f.read()

# Check NB_B and NB_Q values
idx = html.find('var NB_B = ')
if idx >= 0:
    print(f'NB_B: {html[idx:idx+100]}')
else:
    print('NB_B NOT FOUND')
    # Check if placeholder wasn't replaced
    if 'B_JSON_PLACEHOLDER' in html:
        print('WARNING: B_JSON_PLACEHOLDER not replaced!')

idx2 = html.find('var NB_Q = ')
if idx2 >= 0:
    print(f'NB_Q: {html[idx2:idx2+80]}')
else:
    print('NB_Q NOT FOUND')

# Check for any leftover placeholders
for p in ['Q_JSON_PLACEHOLDER', 'B_JSON_PLACEHOLDER', 'DS_DISABLED']:
    if p in html:
        print(f'WARNING: placeholder {p} not replaced!')

# Check the replace() calls in the route function
print(f'\nTemplate source check:')
with open('D:\\Novel-Bridge\\apps\\rag-agent\\app\\api\\demo.py', encoding='utf-8') as f:
    src = f.read()
for line in src.split('\n'):
    if 'replace(' in line and 'PLACEHOLDER' in line:
        print(f'  {line.strip()[:120]}')
