# Remote Server Structure

> Agent-facing deployment structure for Demo 5A.  
> Do not put passwords, tokens, private keys, or real database secrets in this file.

## Target Host

```text
host: 192.168.3.50
ssh_port: 22
user: wk
```

Secrets must come from local `.env`, SSH agent, password prompt, or user-provided runtime input.

## Root Directory

```text
/home/wk/novelbridge
```

## Directory Layout

```text
/home/wk/novelbridge/
  apps/
    llama.cpp/
    rag-agent/
  models/
    qwen3.6-35b-gguf/
  data/
    mysql/
    neo4j/
    chroma/
  logs/
    llama.cpp/
    rag-agent/
    mysql/
    neo4j/
    chroma/
  runtime/
    pids/
    ports/
  env/
  deploy/
    remote/
  scripts/
    remote/
```

## Runtime Decisions

- Use native `llama-server` from `/home/wk/novelbridge/apps/llama.cpp`.
- Do not rely on `llama-cpp-python` server for Demo 5A.
- Use Chroma embedded persistent mode through Python `rag-agent`.
- Chroma data path: `/home/wk/novelbridge/data/chroma`.
- Docker initially failed to pull images through several mirrors, but after the Docker Compose/1Panel setup it successfully pulled `mysql:8.4` and `neo4j:5-community`.
- Use Docker Compose for MySQL and Neo4j in Demo 5A.
- Use native/user-directory runtime only for llama.cpp and the Python `rag-agent`.
- Do not switch Neo4j/MySQL back to tar.gz or apt/system installs unless Docker becomes unavailable again.
- Keep ports fixed during Demo 5A. If a port is occupied, fail clearly and print the owning process.
- Use scripts first; move to `systemd --user` only after Demo 5A is stable.

## Current Remote Status

Verified on 2026-05-16:

```text
novelbridge-mysql  Up  127.0.0.1:13306->3306
novelbridge-neo4j  Up  127.0.0.1:17474->7474, 127.0.0.1:17687->7687
llama-server       Up  127.0.0.1:18080
rag-agent          Up  0.0.0.0:18081
```

`nb_up.sh` health output has reached:

```text
MySQL:          [UP]
Neo4j:          [UP]
Neo4j-HTTP:     [UP]
Chroma:         [UP] (embedded)
llama-server:   [UP]
rag-agent:      [UP]
```

Remaining validation:

```text
Run nb_down.sh, then nb_up.sh again to prove the scripts can restore services from a stopped state rather than only detecting already-running services.
```

## Native llama-server Build Note

The embedded server Web UI can fail during CMake generation on this host. Build the server API without Web UI:

```bash
cmake -B build \
  -DGGML_CUDA=ON \
  -DLLAMA_BUILD_SERVER=ON \
  -DLLAMA_BUILD_UI=OFF \
  -DLLAMA_BUILD_WEBUI=OFF \
  -DLLAMA_USE_PREBUILT_UI=OFF \
  -DLLAMA_USE_PREBUILT_WEBUI=OFF \
  -DLLAMA_BUILD_TESTS=OFF \
  -DGGML_BUILD_TESTS=OFF \
  -DCMAKE_BUILD_TYPE=Release
```

Runtime start pattern:

```bash
nohup /home/wk/novelbridge/apps/llama.cpp/build/bin/llama-server \
  -m "$LLAMA_MODEL" \
  --host 127.0.0.1 \
  --port 18080 \
  -ngl 999 \
  -c 8192 \
  --jinja \
  > /home/wk/novelbridge/logs/llama.cpp/server.log 2>&1 &

echo $! > /home/wk/novelbridge/runtime/pids/llama-server.pid
```

Stop pattern:

```bash
kill "$(cat /home/wk/novelbridge/runtime/pids/llama-server.pid)"
rm -f /home/wk/novelbridge/runtime/pids/llama-server.pid
```

## Ports

| Service | Port | Scope |
|---|---:|---|
| llama-server | 18080 | localhost |
| rag-agent | 18081 | LAN or SSH tunnel |
| MySQL | 13306 | localhost or Docker network |
| Neo4j HTTP | 17474 | localhost or SSH tunnel |
| Neo4j Bolt | 17687 | localhost or SSH tunnel |

## Demo 5A Files Created

| Remote path | Source | Description |
|---|---|---|
| `deploy/remote/ports.env` | `deploy/remote/ports.env` | Centralized port config |
| `deploy/remote/docker-compose.yml` | `deploy/remote/docker-compose.yml` | MySQL + Neo4j containers |
| `deploy/remote/nb_up.sh` | `deploy/remote/nb_up.sh` | Start all services |
| `deploy/remote/nb_down.sh` | `deploy/remote/nb_down.sh` | Stop all services |
| `deploy/remote/nb_status.sh` | `deploy/remote/nb_status.sh` | Service status |
| `deploy/remote/nb_healthcheck.sh` | `deploy/remote/nb_healthcheck.sh` | Health check (JSON support) |
| `deploy/remote/nb_ports.py` | `deploy/remote/nb_ports.py` | Port conflict detection |
| `apps/rag-agent/` | `rag-agent/` | FastAPI service with `/health` |
| Spring Boot config | `RagAgentProperties.java` | `novel-bridge.rag-agent.base-url` |

## Demo 5A Agent Scope (achieved)

- ✅ remote deploy directory and config templates
- ✅ native llama-server start/stop/status scripts
- ✅ rag-agent minimal `/health` (also `/health/llm`, `/health/mysql`, `/health/neo4j`, `/health/vector`)
- ✅ MySQL/Neo4j/Chroma health checks
- ✅ fixed port checks (`nb_ports.py`)
- ✅ Spring Boot `rag-agent` base-url config
- ✅ Docker Compose for MySQL + Neo4j
- ✅ vector-db 已改为 Chroma embedded（无独立容器）

Verify remaining (requires SSH):
- [x] Run `nb_up.sh` on remote
- [x] `nb_healthcheck.sh` returns all UP in human-readable output
- [ ] Run `nb_down.sh`, then `nb_up.sh` from a stopped state
- [ ] `nb_healthcheck.sh --json` returns all UP
- [ ] Spring Boot starts with remote endpoint
