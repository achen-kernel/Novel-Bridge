import urllib.request, json

r = urllib.request.urlopen('http://127.0.0.1:18079/api/v2/pipeline/books')
data = json.loads(r.read())
for b in data.get('books', []):
    bid = b['id']
    title = b['title'][:10]
    for phase in ['P3','P5']:
        info = b.get('phases', {}).get(phase, {})
        st = info.get('latest_status', '?')
        tid = info.get('latest_task_id', '')
        err = ''
        msg = ''
        if tid:
            try:
                r2 = urllib.request.urlopen(f'http://127.0.0.1:18079/api/v2/tasks/{tid}')
                t = json.loads(r2.read())
                err = t.get('error', '')[:300]
                msg = t.get('message', '')[:100]
            except:
                pass
        print(f'[{title}] {phase}: {st}')
        if msg:
            print(f'  msg: {msg}')
        if err:
            print(f'  err: {err}')
