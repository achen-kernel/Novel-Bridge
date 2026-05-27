# NovelBridge

**API-first novel reading and authoring analysis agent.**

```text
Book → Chapter → Chunk → ChapterFact → Evidence/Citation
     → Entity Governance → Retrieval QA → Narrative Graph → Audit/Dataset
```

## Project Structure

```text
Novel-Bridge/
├── apps/rag-agent/              # Python FastAPI backend (active)
│   ├── app/
│   │   ├── api/                 HTTP routes
│   │   ├── pipeline/            Preprocessing P1-P8
│   │   ├── qa/                  QA engine
│   │   ├── eval/                Evaluation system
│   │   ├── quality/             Quality workflow
│   │   ├── agent_runtime/       Agent state/tool contracts
│   │   ├── clients/             External service clients
│   │   ├── stores/              Data access layer
│   │   └── static/              Frontend HTML/CSS/JS
│   └── scripts/                 Ad-hoc scripts
├── deploy/remote/               Docker deployment
├── Novel-Bridge/                Java Spring Boot API shell (secondary)
└── docs/                        Architecture docs
```

## Service Architecture

| Service | Access | Port |
|---------|--------|------|
| MySQL | localhost via SSH tunnel | 13306 |
| Qdrant (vector DB) | localhost via SSH tunnel | 16333 |
| Neo4j (graph) | localhost via SSH tunnel | 17474 / 17687 |
| llama-server (9B) | localhost via SSH tunnel | 18080 |
| Embedding | localhost via SSH tunnel | 18082 |
| DeepSeek API | direct (API key) | — |

All services connect to `127.0.0.1` via SSH tunnels to the remote server.
Configure connection parameters in the `/config` UI or `novel_bridge_config.json`.

## Quick Start

```powershell
# 1. Create config
python D:\Novel-Bridge\manage_server.py start

# 2. Open browser
#    http://127.0.0.1:18079/demo

# 3. Configure services in /config page

# Stop
python D:\Novel-Bridge\manage_server.py stop
```

## Service Responsibilities

| Layer | Responsibility |
|---|---|
| Python FastAPI | Text processing, model calls, extraction, QA, retrieval indexing, quality |
| Java Spring Boot | Product API shell (compile-ready, secondary) |
| MySQL | Source-of-truth for all structured data |
| Qdrant | Vector retrieval (Qwen3-Embedding-0.6B, 1024-dim) |
| Neo4j | Optional narrative graph projection |

## Model & Retrieval Decisions

| Component | Decision |
|---|---|
| DeepSeek API | Prior hints, audit/review, alias safety, risky fact validation |
| Local 9B | Bulk extraction, ChapterFact draft, JSON repair, low-cost candidates |
| Embedding | `Qwen/Qwen3-Embedding-0.6B`, 1024 dimensions, cosine |
| Vector DB | Qdrant (default port 16333) |
| RAG | Evidence-first Hybrid RAG (lexical + dense + structured) |

## Hard Rules

- UTF-8 internally, `utf8mb4` in MySQL.
- No passwords/keys in tracked files. All credentials from environment variables or `novel_bridge_config.json`.
- Model output is candidate data, never truth. Evidence and review decide acceptance.
- Every model call records prompt, revision, provider, duration, errors.

## Commands

```powershell
# Python backend (local dev)
cd apps\rag-agent
python -m uvicorn app.main:app --reload --port 18081

# Java build
cd Novel-Bridge
mvn test

# Server management
python manage_server.py start      # SSH tunnel + uvicorn
python manage_server.py stop       # Stop both
python manage_server.py status     # Server + tunnel health
```

## Configuration

All service connections are configured via the `/config` UI page or by editing `novel_bridge_config.json` directly. See [docs/](docs/) for the full architecture documentation.
