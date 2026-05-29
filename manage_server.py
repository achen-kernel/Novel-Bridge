"""
NovelBridge server manager — start/stop everything with one command.

Services are on a remote server accessed via SSH tunnels (configurable in novel_bridge_config.json).
`start` opens the tunnel + launches uvicorn; `stop` kills both.

Usage:
    python manage_server.py start        # SSH tunnel + uvicorn
    python manage_server.py stop         # Stop uvicorn + close tunnel
    python manage_server.py restart      # Restart all
    python manage_server.py status       # Server + tunnel status
    python manage_server.py tunnel       # Tunnel only (manual)
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request

PORT = 18079
APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "rag-agent")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.log")
PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.pid")

# Remote service ports used to verify SSH tunnel is active
TUNNEL_PORTS = {
    "MySQL": 13306,
    "Qdrant": 16333,
    "Neo4j": 17474,
    "llama": 18080,
    "embedding": 18082,
}


def _load_ssh_config() -> dict:
    """Read SSH config from novel_bridge_config.json, env vars, or built-in defaults.

    Priority: novel_bridge_config.json > env vars (NB_REMOTE_HOST/USER) > built-in defaults.
    New users should configure via /config page, which saves to novel_bridge_config.json.
    """
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "novel_bridge_config.json")
    # Built-in defaults (will be overridden by config file or env vars)
    defaults = {"host": "192.168.3.50", "user": "wk", "port": 22}
    env_host = os.environ.get("NB_REMOTE_HOST")
    env_user = os.environ.get("NB_REMOTE_USER")
    if env_host:
        defaults["host"] = env_host
    if env_user:
        defaults["user"] = env_user
    if not os.path.exists(config_path):
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        ssh = data.get("ssh", {})
        return {
            "host": ssh.get("host") or defaults["host"],
            "user": ssh.get("user") or defaults["user"],
            "port": int(ssh.get("port", defaults["port"])),
        }
    except (json.JSONDecodeError, OSError):
        return defaults


def _read_pid() -> int | None:
    """Read PID from pidfile. Returns None if file missing or invalid."""
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _write_pid(pid: int):
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def _remove_pid():
    try:
        os.remove(PID_FILE)
    except FileNotFoundError:
        pass


def _check_tunnel() -> dict:
    """Probe each remote service port to verify SSH tunnel is active.

    Returns dict of {service_name: True/False}.
    """
    results = {}
    for name, port in TUNNEL_PORTS.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", port))
            s.close()
            results[name] = result == 0
        except Exception:
            results[name] = False
    return results


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running (cross-platform)."""
    try:
        if os.name == "nt":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def is_server_ready() -> bool:
    try:
        r = urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3)
        return r.status == 200
    except Exception:
        return False


def status():
    pid = _read_pid()
    if pid and _is_pid_alive(pid):
        print(f"Server running (PID={pid}, port={PORT})")
        if is_server_ready():
            print(f"  http://127.0.0.1:{PORT}/demo  [healthy]")
        else:
            print("  [not responding yet]")
    else:
        if pid:
            print(f"Stale pidfile found (PID={pid}). Cleaning up.")
            _remove_pid()
        print("Server not running.")

    # Tunnel status
    tunnel = _check_tunnel()
    all_ok = all(tunnel.values())
    print(f"\nSSH Tunnel ({'✅ active' if all_ok else '❌ down'}):")
    for name, ok in tunnel.items():
        icon = "🟢" if ok else "🔴"
        print(f"  {icon} {name:12s}  127.0.0.1:{TUNNEL_PORTS[name]}")

    if not all_ok:
        print("\n  隧道未全部连通。运行: python manage_server.py tunnel")
    return all_ok


def stop():
    pid = _read_pid()
    if pid and _is_pid_alive(pid):
        print(f"Stopping PID {pid}...")
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                               capture_output=True, timeout=10)
            else:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    if not _is_pid_alive(pid):
                        break
                    time.sleep(0.5)
                if _is_pid_alive(pid):
                    os.kill(pid, signal.SIGKILL)
            time.sleep(1)
            print("Uvicorn stopped.")
        except Exception as e:
            print(f"Error stopping: {e}")
    else:
        print(f"No process found (pidfile: {pid})")
    _remove_pid()

    # 2. Close SSH tunnel
    print("Closing SSH tunnel...")
    _tunnel_down()


def tunnel_up() -> bool:
    """Start SSH tunnel to remote server in background.

    Returns True if all tunnel ports are reachable.
    """
    # Skip if tunnel is already up
    already = _check_tunnel()
    if all(already.values()):
        print("SSH Tunnel already active.")
        return True

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "scripts", "remote", "nb_tunnel_up.ps1")
    if not os.path.exists(script):
        print(f"Tunnel script not found: {script}")
        return False

    ssh = _load_ssh_config()
    ssh_host = ssh.get("host", "192.168.3.50")
    ssh_user = ssh.get("user", "wk")
    print(f"Starting SSH tunnel to {ssh_user}@{ssh_host} ...")
    result = subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script,
         "-User", ssh_user, "-RemoteHost", ssh_host],
        capture_output=True, text=True, timeout=30,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(f"Tunnel failed (exit={result.returncode}): {result.stderr[:300]}")
        return False

    time.sleep(2)
    tunnel = _check_tunnel()
    ok = sum(1 for v in tunnel.values() if v)
    print(f"Tunnel ports: {ok}/{len(tunnel)} up")
    if ok < len(tunnel):
        print("Some ports are not responding. Check remote server status.")
    return ok == len(tunnel)


def _tunnel_down():
    """Stop SSH tunnel processes via nb_tunnel_down.ps1."""
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "scripts", "remote", "nb_tunnel_down.ps1")
    if not os.path.exists(script):
        print(f"Tunnel down script not found: {script}")
        return
    ssh = _load_ssh_config()
    subprocess.run(
        ["powershell", "-ExecutionPolicy", "Bypass", "-File", script,
         "-RemoteHost", ssh.get("host", "192.168.3.50")],
        capture_output=True, timeout=15,
    )


def start():
    # 1. Open SSH tunnel if not already up
    tunnel_ok = tunnel_up()
    if not tunnel_ok:
        print("\n⚠ 部分服务端口不通，继续启动可能部分功能不可用。")

    # Check if already running
    pid = _read_pid()
    if pid and _is_pid_alive(pid):
        print(f"Server already running (PID={pid}).")
        if not is_server_ready():
            print("  (process exists but not responding)")
        return

    # Clean up stale pidfile
    _remove_pid()

    if not os.path.isdir(APP_DIR):
        print(f"Error: {APP_DIR} not found. Run this script from the project root.")
        return

    print(f"Starting server on port {PORT}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", f"--port={PORT}"],
        cwd=APP_DIR,
        stdout=open(LOG_FILE, "w"),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    _write_pid(proc.pid)
    print(f"  PID={proc.pid} written to {PID_FILE}")

    # Wait for readiness
    t0 = time.time()
    while time.time() - t0 < 30:
        if is_server_ready():
            print(f"Server ready in {time.time() - t0:.0f}s.")
            print(f"  http://127.0.0.1:{PORT}/demo")
            return
        if proc.poll() is not None:
            print(f"Server exited early (code {proc.returncode}). Check {LOG_FILE}")
            try:
                with open(LOG_FILE, "r") as f:
                    print(f.read()[:500])
            except Exception:
                pass
            _remove_pid()
            return
        time.sleep(1)

    print(f"Timeout after 30s. Check {LOG_FILE}")
    _remove_pid()


def restart():
    stop()
    time.sleep(1)
    start()


def restart_remote():
    """SSH into remote server and restart all services (Docker + llama + embedding).

    Docker containers (mysql, qdrant, neo4j) have 'unless-stopped' policy
    and auto-restart, but the remote nb_up.sh handles them too if needed.
    """
    ssh = _load_ssh_config()
    host = ssh.get("host", "192.168.3.50")
    user = ssh.get("user", "wk")
    port = ssh.get("port", 22)
    remote_deploy = f"/home/wk/novelbridge/deploy/remote"

    ssh_base = ["ssh", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new",
                "-p", str(port), f"{user}@{host}"]

    print(f"Connecting to {user}@{host}:{port} ...")

    # 1. Check current state
    try:
        r = subprocess.run(
            ssh_base + ["docker ps --format '{{.Names}} {{.Status}}'"],
            capture_output=True, text=True, timeout=10,
        )
        print("  Docker containers:")
        for line in r.stdout.strip().split('\n'):
            if line:
                print(f"    {line}")

        r = subprocess.run(
            ssh_base + [
                "echo llama=$(ps aux | grep -c '[l]lama-server'); "
                "echo embed=$(ps aux | grep -c '[e]mbedding')"
            ],
            capture_output=True, text=True, timeout=10,
        )
        for line in r.stdout.strip().split('\n'):
            if 'llama=' in line:
                ok = '0' not in line.split('=')[1]
                print(f"  llama-server: {'🟢 running' if ok else '🔴 down'}")
            if 'embed=' in line:
                ok = '0' not in line.split('=')[1]
                print(f"  embedding:    {'🟢 running' if ok else '🔴 down'}")
    except Exception as e:
        print(f"  SSH check failed: {e}")
        return False

    # 2. Run nb_up.sh — handles Docker + llama + embedding
    print("\n🔄 Running nb_up.sh to restart all remote services...")
    try:
        subprocess.run(
            ssh_base + [f"bash {remote_deploy}/nb_up.sh"],
            timeout=300,  # 5 min timeout for model loading
        )
        print("  nb_up.sh completed")
    except subprocess.TimeoutExpired:
        print("  nb_up.sh timed out (model loading may still be in progress)")
    except Exception as e:
        print(f"  nb_up.sh failed: {e}")

    # 3. Wait for remote services to bind ports (Docker may take a moment)
    print("\nWaiting for remote ports to be ready...")
    for i in range(15):
        try:
            r = subprocess.run(
                ssh_base + ["ss -tlnp | grep -cE '13306|16333|17474|18080|18082'"],
                capture_output=True, text=True, timeout=10,
            )
            count = int(r.stdout.strip() or '0')
            if count >= 5:
                print(f"  All 5 remote ports ready after {i*2}s")
                break
            print(f"  [{i*2}s] {count}/5 ports ready", end="\r")
        except Exception:
            pass
        time.sleep(2)

    # 4. Restart local SSH tunnel to pick up new container connections
    print("\n🔄 Restarting SSH tunnel...")
    _tunnel_down()
    time.sleep(2)
    for attempt in range(3):
        if tunnel_up():
            break
        print(f"  Tunnel attempt {attempt+1} failed, retrying in 5s...")
        _tunnel_down()
        time.sleep(5)
    time.sleep(3)

    # 4. Verify
    print("\nVerifying all services...")
    for i in range(30):
        tunnel = _check_tunnel()
        all_ok = all(tunnel.values())
        status = " ".join(f"{k}={'🟢' if v else '🔴'}" for k, v in tunnel.items())
        print(f"  [{i*2+2}s] {status}", end="\r")
        if all_ok:
            print(f"\n  ✅ All services up after {(i+1)*2}s")
            return True
        time.sleep(2)
    print()

    print("\nFinal status:")
    tunnel = _check_tunnel()
    for name, ok in tunnel.items():
        icon = "🟢" if ok else "🔴"
        print(f"  {icon} {name:12s}  {'OK' if ok else 'DOWN'}")

    return all(tunnel.values())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python manage_server.py tunnel|start|stop|restart|status|restart-remote")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "tunnel":
        tunnel_up()
    elif action == "start":
        start()
    elif action == "stop":
        stop()
    elif action == "restart":
        restart()
    elif action == "restart-remote":
        restart_remote()
    elif action == "status":
        status()
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
