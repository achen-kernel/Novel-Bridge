"""
Full auto pipeline: start server → run P1-P8 for books 6-10 → report.
"""
import subprocess, sys, time, urllib.request, json, os

API = "http://127.0.0.1:18079"
BOOKS = [(6,"西游记"),(7,"聊斋志异"),(8,"搜神记"),(9,"山海经"),(10,"水浒传")]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# 1. Start server
log("Starting server...")
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app")
proc = subprocess.Popen(
    ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port=18079"],
    cwd=os.path.dirname(APP_DIR),
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)

# Wait for ready
t0 = time.time()
while time.time() - t0 < 60:
    try:
        r = urllib.request.urlopen(f"{API}/health", timeout=3)
        if r.status == 200:
            log(f"Server ready in {time.time()-t0:.0f}s (PID={proc.pid})")
            break
    except: pass
    time.sleep(1)
else:
    log("Server failed to start!"); sys.exit(1)

# 2. Run pipeline for each book
def call(method, path, body=None, timeout=600):
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", 18079, timeout=timeout)
    headers = {"Content-Type": "application/json"}
    b = json.dumps(body).encode() if body else None
    conn.request(method, path, body=b, headers=headers)
    r = conn.getresponse()
    data = json.loads(r.read().decode())
    conn.close()
    return data

PHASES = ["P1","P2","P3","P4","P5","P6","P7","P8"]
PHASE_NAMES = {"P1":"分章","P2":"梗概","P3":"提取","P4":"治理","P5":"叙事","P6":"索引","P7":"图谱","P8":"导出"}

for bid, bname in BOOKS:
    log(f"\n{'='*40}")
    log(f"  {bname}({bid})")
    log(f"{'='*40}")
    
    for phase in PHASES:
        sys.stdout.write(f"  {phase} {PHASE_NAMES[phase]}... ")
        sys.stdout.flush()
        t0 = time.time()
        
        # Trigger phase
        r = call("POST", f"/api/v2/books/{bid}/phase/{phase}", {"use_model": False}, timeout=600)
        task_id = r.get("task_id", "")
        
        if not task_id or r.get("status") != "started":
            log(f"FAIL (trigger: {r})")
            continue
        
        # Poll for completion
        for _ in range(300):  # 10 min max
            t = call("GET", f"/api/v2/tasks/{task_id}", timeout=10)
            st = t.get("status", "PENDING")
            if st in ("SUCCESS",):
                log(f"OK  ({time.time()-t0:.0f}s)")
                break
            elif st in ("FAILED", "CANCELLED"):
                err = t.get("error", "")[:100]
                log(f"FAIL ({err})")
                break
            time.sleep(2)
        else:
            log(f"TIMEOUT")

# 3. Report
log(f"\n{'='*40}")
log(f"  Pipeline complete!")
log(f"{'='*40}")
for bid, bname in BOOKS:
    r = call("GET", f"/api/v2/pipeline/books", timeout=10)
    for b in r.get("books", []):
        if b["id"] == bid:
            phases = b.get("phases", {})
            statuses = {p: phases[p]["latest_status"] for p in PHASES}
            log(f"  {bname}: {statuses}")

log(f"\nServer PID={proc.pid}")
log(f"Open http://127.0.0.1:18079/demo to test.")
