with open('D:/Novel-Bridge/apps/rag-agent/app/api/frontend.py','r',encoding='utf-8') as f:
    c = f.read()
n = c.count('async function refreshStatus')
print(f'Count of async function refreshStatus: {n}')
if n == 1:
    print('OK - only one definition')
else:
    print(f'BUG - {n} definitions!')
