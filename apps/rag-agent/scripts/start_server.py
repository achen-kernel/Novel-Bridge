"""
Start uvicorn server in background and wait for it to be ready.
Usage:
    python scripts/start_server.py
    python scripts/start_server.py --port 18079
"""
import subprocess
import sys
import time
import urllib.request
import os

PORT = "18079"
if "--port" in sys.argv:
    idx = sys.argv.index("--port")
    PORT = sys.argv[idx + 1]

APP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app")

print(f"Starting uvicorn on port {PORT}...")
proc = subprocess.Popen(
    ["python", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", f"--port={PORT}", "--reload"],
    cwd=os.path.dirname(APP_DIR),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
)

# Wait for server to be ready (up to 30s)
start = time.time()
last_line = ""
while time.time() - start < 30:
    if proc.poll() is not None:
        print(f"Server exited early with code {proc.returncode}")
        sys.exit(1)
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
        if r.status == 200:
            elapsed = time.time() - start
            print(f"Server ready in {elapsed:.1f}s (PID={proc.pid})")
            print(f"  Health: {r.read().decode()[:100]}")
            print(f"  Server PID: {proc.pid}")
            sys.exit(0)
    except Exception:
        pass
    time.sleep(0.5)

print(f"Server did not become ready within 30s. PID={proc.pid}")
sys.exit(1)
