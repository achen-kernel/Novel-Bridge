# NovelBridge Private Context For Codex

> This file is for user-guided Codex sessions only.
> It is intentionally under `docs/private/`, which is gitignored.
> Other coding agents should ignore it unless the user explicitly asks them to read it.
> Do not put server passwords, database passwords, API tokens, private keys, or real `.env` values here.

## Snapshot

- Date: 2026-05-17
- Project: NovelBridge / NovelBridge-Agents
- Current phase: `demo-5a-remote-foundation`
- Current goal: finish a small working NovelBridge demo first, then harden and extend it.
- Main learning goal: use vibe coding to build the project while improving project planning, harness thinking, Java backend ability, and Python AI/RAG engineering ability.

## Repository Shape

Local root:

```text
D:\Novel-Bridge
```

Important local paths:

```text
AGENTS.md
.opencode/skills/vibe-learn/
.vtl/vtl-adapter.json
docs/learn/
docs/personal-notes/
docs/private/current-context-for-codex.md
Novel-Bridge/                 # Java / Spring Boot backend
rag-agent/                    # Python FastAPI service
deploy/remote/                # Remote Linux service scripts/config
scripts/remote/               # Windows PowerShell SSH wrappers
novel_bridge_demo_5_gbnf_开发需求文档_v_0_1.md
```

Tracked learning docs that normal agents may read:

```text
docs/learn/vtl-state.json
docs/learn/current-stage.md
docs/learn/project-skeleton.md
docs/learn/demo-plan.md
docs/learn/remote-server-structure.md
docs/learn/table-design-review.md
docs/learn/table-design.md
docs/learn/retro-log.md
docs/learn/personal-vibecoding-playbook.md
docs/learn/vtl-feedback-log.md
```

Private docs:

```text
docs/private/
```

These are for this user-guided Codex context only and should not be read by ordinary implementation agents.

## Project Direction

NovelBridge is a local-first AI/RAG system for processing novels/books.

The intended architecture:

- Java/Spring Boot backend: main business API, database-facing domain model, user-facing orchestration entry.
- Python `rag-agent`: LLM calls, text chunking, extraction, Chroma vector persistence, Neo4j graph writes, evaluation/data export later.
- Remote Linux server: local model inference and data services.
- MySQL: relational metadata and workflow records.
- Neo4j: knowledge graph.
- Chroma: embedded vector store inside `rag-agent`.
- llama.cpp native `llama-server`: local OpenAI-compatible LLM endpoint.

Do not implement the full final platform in one pass. The project follows demo-first slicing.

## Demo Plan

Current split:

```text
Demo 5A -> remote Linux service foundation
Demo 5B -> chunk + model_run + entity extraction candidate + review
Demo 6  -> relation/event/claim extraction and graph hardening
Demo 7  -> GraphRAG QA, evaluation, fine-tuning data preparation
```

Demo 5A is focused only on remote infrastructure:

- remote directories
- fixed ports
- startup/shutdown/status/health scripts
- MySQL and Neo4j availability
- Chroma persistent path
- native `llama-server`
- Python `rag-agent`
- Spring Boot config entry for `rag-agent`

Demo 5A should not implement:

- full GraphRAG
- relation/event/claim extraction
- wiki alignment
- fine-tuning
- complex graph visualization
- full frontend review UI
- production-grade service manager

## Current Remote Server

Remote host info that may appear in tracked docs:

```text
host: 192.168.3.50
ssh_port: 22
user: wk
```

Do not write the SSH password anywhere.

Remote root:

```text
/home/wk/novelbridge
```

Remote layout:

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
  deploy/
    remote/
  scripts/
    remote/
```

Model:

```text
/home/wk/novelbridge/models/qwen3.6-35b-gguf/Qwen_Qwen3.6-35B-A3B-Q8_0.gguf
```

Ports:

| Service | Port | Notes |
|---|---:|---|
| MySQL | 13306 | Docker Compose, localhost binding |
| Neo4j HTTP | 17474 | Docker Compose |
| Neo4j Bolt | 17687 | Docker Compose |
| llama-server | 18080 | native llama.cpp binary, localhost binding |
| rag-agent | 18081 | FastAPI, exposed on `0.0.0.0` |
| Chroma | none | embedded in `rag-agent` |

## Remote Validation Status

As of 2026-05-17, user tested a real stop/start cycle:

```bash
cd /home/wk/novelbridge/deploy/remote
bash nb_down.sh
bash nb_up.sh
bash nb_status.sh
bash nb_healthcheck.sh --json
```

Observed results:

- `nb_down.sh` stopped `rag-agent`, `llama-server`, Neo4j, and MySQL.
- `nb_up.sh` restarted `llama-server` and `rag-agent`.
- MySQL and Neo4j ports were already listening after Docker stop/start behavior; health checks still reported them as UP.
- `nb_status.sh` showed:
  - MySQL `:13306` up
  - Neo4j Bolt `:17687` up
  - Neo4j HTTP `:17474` up
  - llama-server `:18080` running with PID
  - rag-agent `:18081` running with PID
- `nb_healthcheck.sh --json` returned top-level `"status": "UP"`.
- Windows local call worked:

```powershell
Invoke-RestMethod http://192.168.3.50:18081/health
```

Returned:

```text
status          : UP
llama_cpp       : UP
mysql           : UP
neo4j           : UP
vector          : MOCK
model           : Qwen3.6-35B-A3B
grammar_enabled : True
```

Important nuance:

- `nb_up.sh` human output may still show `llama-server:[MOCK (port open but /health not responding)]`.
- The JSON healthcheck correctly reports `llama_cpp.status = UP` and `mock = false`.
- Native llama.cpp should be checked via `/v1/models`, not only `/health`.

Docker nuance:

- There were earlier Docker Hub / mirror issues.
- After Docker Compose / 1Panel setup, MySQL and Neo4j images were pulled and containers started successfully.
- There were also earlier Docker socket permission issues. If they reappear, verify user group membership and re-login.
- Do not waste time repeatedly reconfiguring Docker mirrors unless image pulling fails again.

## Known Deployment Pitfalls

See:

```text
docs/personal-notes/server-setup-pitfalls.md
```

Key lessons:

- Do not use `llama-cpp-python` server as the main route; it failed with temporary name resolution errors on this host.
- Use native `llama-server`.
- Build llama.cpp without embedded Web UI if CMake fails in `tools/ui` / `xxd.cmake`.
- `.env` should be copied from `.env.example`, not rewritten as a tiny file.
- Neo4j password must be at least 8 characters.
- Do not use shell-special characters carelessly in `.env` values because scripts may `source` the file.
- Chroma is embedded in `rag-agent`; no separate Chroma server/container for Demo 5A.

## Skill State

Project skill:

```text
.opencode/skills/vibe-learn/
```

Current skill intent:

- demo-first development
- scope slicing
- compact project docs
- evidence before completion
- retro and personal playbook
- optional practice snapshots
- Java and Python learning lanes

Recent skill updates:

- Added `Scope Slicing Rule`.
- Changed hard practice requirement into `Practice decision`.
- Added `SKIP-PRACTICE` support for infrastructure/deploy/prompt-only stages.
- Added `Python Learning Lane`.

Python learning rule:

```text
Practice Python through real project code:
rag-agent endpoints, typed schemas, LLM client code, text chunking, extraction validation,
Chroma persistence, Neo4j writes, and evaluation scripts.
Do not invent unrelated Python exercises.
```

## Harness Thinking

The project has two practical harness layers:

1. Development/learning harness:
   - `.opencode/skills/vibe-learn`
   - `.vtl/vtl-adapter.json`
   - `docs/learn/vtl-state.json`
   - `docs/learn/current-stage.md`
   - `vtl_status.py`, `vtl_scan.py`, `vtl_closing.py`

2. Runtime/project harness:
   - `AgentRun` / `AgentStep` style records for long-running work
   - `Citation` for QA evidence
   - remote start/stop/status/health scripts
   - fixed ports and service status
   - later extraction/review/evaluation traces

Important rule:

```text
Do not call a long-running build/query flow complete without trace records.
Do not call QA complete without citations.
```

## Current Next Step

Suggested next main implementation stage:

```text
Demo 5B: chunk + model_run + entity extraction candidate + review
```

Likely Demo 5B scope:

- Send a small sample text/chapter to `rag-agent`.
- Add minimal chunking.
- Call remote `llama-server` for structured entity extraction.
- Store model run / agent run trace.
- Store extraction candidates in MySQL.
- Optionally write minimal approved entities to Neo4j.
- Keep Chroma usage minimal unless needed.
- Return evidence through API/health/test output.

Do not jump directly to full relation graph, GraphRAG QA, fine-tuning, or frontend-heavy workflows.

## Suggested Prompt For New Codex Guidance Session

Use this when starting a new Codex guidance session, not for ordinary implementation agents:

```text
请先阅读 D:\Novel-Bridge\docs\private\current-context-for-codex.md，
再阅读 AGENTS.md 和 docs/learn/current-stage.md。
你是指导和架构复盘 agent，不直接替代开发 agent。
请基于当前 Demo 5A 已跑通的远程服务状态，帮我规划 Demo 5B 的最小闭环，
同时继续维护 vibe-learn skill、学习资产和 Python/Java 学习线。
不要把 docs/private 下的内容加入 git，也不要要求普通开发 agent 默认读取它。
```

## What To Tell Implementation Agents

For a fresh implementation agent, usually do not show this private document. Give it:

```text
请从 AGENTS.md 开始，按 Read First 读取项目状态。
当前只做 Demo 5B 的最小闭环，不做完整 GraphRAG、关系/事件/Claim、微调或复杂前端。
所有远程服务通过 /home/wk/novelbridge/deploy/remote/nb_status.sh 和 nb_healthcheck.sh 检查。
不要读取 docs/private/，除非我明确要求。
```

## Verification Commands

Local:

```powershell
python .opencode\skills\vibe-learn\scripts\vtl_status.py --root . --json
python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json
```

Remote:

```bash
cd /home/wk/novelbridge/deploy/remote
bash nb_status.sh
bash nb_healthcheck.sh --json
```

Windows to remote:

```powershell
Invoke-RestMethod http://192.168.3.50:18081/health
```
