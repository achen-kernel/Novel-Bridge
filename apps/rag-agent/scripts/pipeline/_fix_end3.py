with open('D:/Novel-Bridge/apps/rag-agent/scripts/pipeline/_continue_run.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('log("', 'sys.stdout.write("')
c = c.replace(', end="")', ')\nsys.stdout.flush()')
with open('D:/Novel-Bridge/apps/rag-agent/scripts/pipeline/_continue_run.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')
