with open('app/api/demo.py', encoding='utf-8') as f:
    c = f.read()

target = "esc(m.content).replace(/\\\\n/g,'<br>')+dt+'</div></div>'"
replacement = "esc(m.content).replace(/\\\\n/g,'<br>').replace(/\\(基于模型知识\\)/g,'<strong>(基于模型知识)</strong>')+dt+'</div></div>'"

if target in c:
    c = c.replace(target, replacement)
    with open('app/api/demo.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('OK - bold fix applied')
else:
    print('Pattern not found')
    # Find what's actually there
    idx = c.find("esc(m.content).replace")
    if idx >= 0:
        print(f'Found: {c[idx:idx+120]}')
