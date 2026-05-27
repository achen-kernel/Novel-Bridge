import re
with open('D:/Novel-Bridge/apps/rag-agent/scripts/pipeline/_direct_run.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace(', end=" ")', ')')
c = c.replace(", end=' ')", ')')
with open('D:/Novel-Bridge/apps/rag-agent/scripts/pipeline/_direct_run.py', 'w', encoding='utf-8') as f:
    f.write(c)
print('Fixed')
