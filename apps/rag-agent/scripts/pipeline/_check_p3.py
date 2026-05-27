import urllib.request, json

r = urllib.request.urlopen('http://127.0.0.1:18079/api/v2/pipeline/books')
data = json.loads(r.read())
for b in data.get('books', []):
    bid = b['id']
    title = b['title'][:10]
    p3 = b.get('phases', {}).get('P3', {})
    st = p3.get('latest_status', '?')
    task_id = p3.get('latest_task_id', '')
    print(f'Book {bid} {title}: P3={st} task={task_id}')
    if task_id:
        r2 = urllib.request.urlopen(f'http://127.0.0.1:18079/api/v2/tasks/{task_id}')
        t = json.loads(r2.read())
        err = t.get('error', '')[:200]
        msg = t.get('message', '')
        print(f'  error={err}')
        print(f'  message={msg}')
