"""Fix: make (基于模型知识) bold in chat rendering."""
with open('D:\\Novel-Bridge\\apps\\rag-agent\\app\\api\\demo.py', encoding='utf-8') as f:
    content = f.read()

old = "h+='<div class=\"msg a\"><div class=\"b\">'+mc+esc(m.content).replace(/\\n/g,'<br>')+dt+'</div></div>'"
new = "h+='<div class=\"msg a\"><div class=\"b\">'+mc+esc(m.content).replace(/\\n/g,'<br>').replace(/\\(基于模型知识\\)/g,'<strong>(基于模型知识)</strong>')+dt+'</div></div>'"

if old in content:
    content = content.replace(old, new)
    with open('D:\\Novel-Bridge\\apps\\rag-agent\\app\\api\\demo.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK - replaced')
else:
    print('NOT FOUND - checking alternatives')
    # Try to find similar pattern
    idx = content.find('esc(m.content).replace')
    if idx >= 0:
        print(f'Found at {idx}: {content[idx:idx+100]}')
