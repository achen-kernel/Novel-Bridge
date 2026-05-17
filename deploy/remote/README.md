# NovelBridge — 远程部署

## 服务器结构

```
/home/wk/novelbridge/
├── apps/
│   ├── llama.cpp/              ← llama-server 可执行文件
│   └── rag-agent/              ← Python FastAPI 服务
├── models/
│   └── qwen3.6-35b-gguf/       ← GGUF 模型文件
├── data/
│   ├── mysql/                  ← MySQL 数据（Docker volume）
│   ├── neo4j/                  ← Neo4j 数据（Docker volume）
│   └── chroma/                 ← Chroma 持久化（内嵌）
├── logs/
│   ├── llama.cpp/
│   ├── rag-agent/
│   ├── mysql/
│   ├── neo4j/
│   └── chroma/
├── runtime/
│   ├── pids/                   ← 进程 PID 文件
│   └── ports/                  ← 运行时端口记录
├── env/                        ← 环境变量文件
├── deploy/
│   └── remote/                 ← 本目录（启动/停止/检查脚本）
└── scripts/
    └── remote/                 ← 额外远程脚本（预留）
```

## 部署文件清单

### deploy/remote/（共 10 文件）

| 文件 | 功能 |
|---|---|
| `ports.env` | 集中端口配置 |
| `services.yaml` | 服务定义元数据 |
| `docker-compose.yml` | MySQL + Neo4j 容器定义 |
| `.env.example` | 环境变量模板（不含密码） |
| `nb_ports.py` | 端口检查工具 |
| `nb_up.sh` | 一键启动所有服务 |
| `nb_down.sh` | 一键停止所有服务 |
| `nb_status.sh` | 服务状态检查 |
| `nb_healthcheck.sh` | 详细健康检查 |
| `README.md` | 本文件 |

### rag-agent（5 文件 → 服务器 `apps/rag-agent/`）

| 文件 | 功能 |
|---|---|
| `app/main.py` | FastAPI 应用，含 `/health` + 5 个子端点 |
| `app/__init__.py` | 包初始化 |
| `requirements.txt` | Python 依赖 |
| `.env.example` | 环境变量模板 |
| `run.sh` | 启动脚本 |

## 端口分配

| 服务 | 端口 | 绑定 | 方式 |
|---|---|---|---|
| llama-server | 18080 | 127.0.0.1 | 原生二进制 |
| rag-agent | 18081 | 0.0.0.0 | Python FastAPI |
| MySQL | 13306 | 127.0.0.1 | Docker |
| Neo4j HTTP | 17474 | 127.0.0.1 | Docker |
| Neo4j Bolt | 17687 | 127.0.0.1 | Docker |

## 快速开始

```bash
# 1. 首次准备
cd /home/wk/novelbridge/deploy/remote
cp .env.example .env
vi .env   # 填入密码和路径

# 2. 检查端口
python3 nb_ports.py

# 3. 一键启动
bash nb_up.sh

# 4. 查看状态
bash nb_status.sh

# 5. 健康检查
bash nb_healthcheck.sh --json

# 6. 停止
bash nb_down.sh
```

## 安全说明

- 仅 `NB_REMOTE_HOST`/`PORT`/`USER` 和端口可以出现在仓库中
- 所有敏感信息（`MYSQL_ROOT_PASSWORD`、`NEO4J_AUTH` 等）在 `.env` 中
- `.env` 已在 `.gitignore` 中，不会提交到仓库
- llama-server / MySQL / Neo4j 默认只绑定 127.0.0.1

## Mock 说明

| 服务 | 状态 | 说明 |
|---|---|---|
| MySQL | ✅ real | Docker |
| Neo4j | ✅ real | Docker |
| Chroma | ✅ real | 内嵌在 rag-agent |
| llama-server | ⚠️ mock | 小模型 smoke test 阶段 |
| rag-agent | ✅ real | 最小 `/health` |

## 依赖

- 远程服务器: `bash`, `docker`, `docker compose`, `python3`, `ss`, `curl`
- llama-server: 预编译二进制或源码编译（`make -j`）
