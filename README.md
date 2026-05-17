# NovelBridge — 智能阅读分析系统

一个双端协作的小说/书籍智能阅读与分析系统。

```
本地端（Windows / Spring Boot）
  ├─ 上传整本书到远程 MySQL
  ├─ 触发远端 rag-agent 构建管线
  └─ 前端展示、业务入口

远端（Linux / Python + llama.cpp）
  ├─ 章节切分 + 文本分块
  ├─ 本地大模型实体抽取（2×RTX 3090）
  ├─ 候选审核 + Neo4j 图谱写入
  └─ Chroma 向量索引
```

> 当前阶段：**Demo 5B — 实体抽取闭环**（已完成）

---

## 双端架构

```
┌─ Windows 本地（本地端）──────────────────────────┐
│                                                   │
│  Spring Boot 后端 (:8080)                         │
│    ├─ 上传书籍 → novel_book_source（远程 MySQL）  │
│    ├─ 触发远端 POST /build?source_id=X            │
│    ├─ AgentRun / AgentStep 追踪                     │
│    └─ 前端展示、查询入口                           │
│                                                   │
│  PowerShell 管理脚本 (scripts/remote/)             │
│    ├─ nb_remote_*.ps1         SSH → 远程启停      │
│    ├─ nb_tunnel_*.ps1         SSH 端口转发        │
│    └─ nb_sync_from_remote.ps1 远端文件同步         │
│                                                   │
└──────────────────┬────────────────────────────────┘
                   │ SSH Tunnel / HTTP
                   ▼
┌─ Linux 远程（远端）──────────────────────────────┐
│                                                   │
│  rag-agent (:18081)   Python 构建编排层           │
│    ├─ POST /build      书籍构建管线（全自动）     │
│    │   ├─ 书籍总览分析（LLM 前 6000 字）          │
│    │   ├─ 章节切分（规则 + LLM 辅助）             │
│    │   ├─ 文本分块（800-1500 字，200 重叠）       │
│    │   ├─ 实体抽取（每块调 LLM，~60-80 tok/s）   │
│    │   ├─ 候选入库 + evidence 校验               │
│    │   └─ 等待人工审核                            │
│    ├─ GET  /review/candidates    查看候选         │
│    ├─ POST /review/.../approve   审核通过         │
│    └─ POST /review/.../reject    审核拒绝         │
│                                                   │
│  基础设施                                          │
│    ├─ llama-server (:18080)   双卡 3090 推理      │
│    ├─ MySQL (:13306)          15 表持久化          │
│    ├─ Neo4j (:17474/:17687)   知识图谱             │
│    └─ Chroma (内嵌)           向量存储             │
│                                                   │
│  一键启停 (deploy/remote/)                         │
│    ├─ nb_up.sh / nb_down.sh                       │
│    ├─ nb_status.sh / nb_healthcheck.sh            │
│    └─ nb_ports.py                                 │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## 本地项目结构

```
Novel-Bridge/
│
├── Novel-Bridge/                  ← Spring Boot 后端 (Maven / Java 21)
│   ├── src/main/java/com/achen/novelbridge/
│   │   ├── common/                ← 基础设施（配置、异常、响应、工具）
│   │   ├── pojo/                  ← 数据模型（DTO / Entity / VO）
│   │   └── server/                ← 业务逻辑（controller/mapper/service）
│   └── src/main/resources/
│       ├── application.yml        ← 公共配置（默认 profile=local）
│       ├── application-local.yml  ← 本地开发（直连本地 MySQL :3306）
│       ├── application-dev.yml    ← 远程开发（通过 SSH tunnel 连 :13306）
│       └── schema.sql             ← 数据库建表脚本
│
├── deploy/remote/                 ← 上传到远程服务器的部署文件
│   ├── docker-compose.yml         ← MySQL + Neo4j 容器定义
│   ├── ports.env                  ← 所有服务端口集中配置
│   ├── services.yaml              ← 服务元数据（启动/停止/健康检查方式）
│   ├── nb_up.sh / nb_down.sh      ← 一键启停
│   ├── nb_status.sh / nb_healthcheck.sh  ← 状态/健康检查
│   ├── nb_ports.py                ← 端口冲突检测工具
│   ├── .env.example               ← 环境变量模板（不含密码）
│   └── README.md                  ← 远程部署说明
│
├── scripts/remote/                ← 留在本地的 PowerShell SSH 管理脚本
│   ├── nb_remote_up.ps1           ← SSH 调用 nb_up.sh
│   ├── nb_remote_down.ps1         ← SSH 调用 nb_down.sh
│   ├── nb_remote_status.ps1       ← SSH 调用 nb_status.sh
│   ├── nb_remote_healthcheck.ps1  ← SSH 调用 nb_healthcheck.sh
│   ├── nb_tunnel_up.ps1           ← 建立 SSH 端口转发
│   └── nb_tunnel_down.ps1         ← 关闭 SSH 端口转发
│
├── rag-agent/                     ← Python FastAPI 服务（上传到远程 apps/rag-agent/）
│   ├── app/main.py                ← FastAPI 应用（/health 及子端点）
│   ├── requirements.txt           ← Python 依赖
│   ├── run.sh                     ← 启动脚本
│   ├── .env.example               ← 环境变量模板
│   └── README.md                  ← 部署说明
│
├── docs/
│   ├── learn/                     ← 学习文档（阶段状态、复盘、计划等）
│   └── personal-notes/            ← 服务器环境踩坑记录（不强制 agent 阅读）
│       └── server-setup-pitfalls.md
│
├── .opencode/skills/vibe-learn/   ← AI 辅助开发技能包
├── .vtl/                          ← 项目结构适配器
└── AGENTS.md                      ← AI 助手的项目入口
```

---

## 远程服务器结构（`~/novelbridge/`）

```
~/novelbridge/
├── apps/
│   ├── llama.cpp/              ← llama-server 可执行文件
│   └── rag-agent/              ← Python FastAPI 服务
├── models/
│   └── qwen3.6-35b-gguf/       ← GGUF 模型文件
├── data/
│   ├── mysql/                  ← MySQL 数据卷
│   ├── neo4j/                  ← Neo4j 数据卷
│   └── chroma/                 ← Chroma 持久化
├── logs/                       ← 各服务日志
├── runtime/pids/               ← 进程 PID 文件
├── env/                        ← 环境变量文件
└── deploy/remote/              ← 启动脚本（同本地 deploy/remote/）
```

---

## 端口分配

所有端口在 `deploy/remote/ports.env` 集中定义，不散落在代码中。

| 服务 | 端口 | 绑定 | 方式 |
|---|---|---|---|
| MySQL | 13306 | 127.0.0.1 | Docker |
| Neo4j HTTP | 17474 | 127.0.0.1 | Docker |
| Neo4j Bolt | 17687 | 127.0.0.1 | Docker |
| llama-server | 18080 | 127.0.0.1 | 原生二进制 |
| rag-agent | 18081 | 0.0.0.0 | Python FastAPI |

---

## 配置与 Profile

Spring Boot 通过 profile 切换数据库连接：

| Profile | 用途 | MySQL | 启动方式 |
|---|---|---|---|
| `local`（默认） | 本地开发、`mvn test` | `localhost:3306` | 直接运行 |
| `dev` | 连远程开发环境 | `localhost:13306`（→ tunnel → 远程） | 先开 tunnel，再 `-Dspring.profiles.active=dev` |

日常开发流程：
```powershell
# 1. 开 SSH tunnel
.\scripts\remote\nb_tunnel_up.ps1

# 2. 启动 Spring Boot（IDEA VM options）
-Dspring.profiles.active=dev
```

---

## 模块功能

### 本地端（Spring Boot / Windows）
- **上传入口**：`POST /api/book-sources/upload` → 写入 `novel_book_source`（含 raw_text）
- **远端触发**：上传后自动调用远程 rag-agent `POST /build?source_id=X`
- **任务追踪**：AgentRun / AgentStep 记录上传和触发过程
- **配置双 profile**：`local`（本地 MySQL） / `dev`（SSH tunnel → 远程 MySQL）
- **开发 tunnel**：`nb_tunnel_up.ps1` 打通本地到远程的端口转发

### 远端（rag-agent / Python + llama.cpp / Linux）
- **书籍构建管线**：`POST /build` 全自动串联
  - 书籍总览分析（LLM 读取前 6000 字判断结构类型）
  - 章节切分（规则识别 第X回/章/卷/篇 + LLM 辅助）
  - 文本分块（800-1500 字，200 字重叠，不跨章）
  - 实体抽取（每块一次 LLM 调用，~60-80 tok/s 双卡）
  - 候选入库（evidence 原文校验 + 字段非空 + 类型枚举）
- **人工审核**：候选 approve / reject / edit → 通过后写入 Neo4j
- **数据追踪**：每次 LLM 调用记录到 `novel_model_run`，prompt/output/error 全部持久化
- **双卡 GPU**：2×RTX 3090，Qwen3.6-35B-A3B MoE，NGL=99（全量 GPU）

### 部署脚本
- **远程 Linux 脚本**：一键启停 MySQL / Neo4j / llama-server / rag-agent
- **本地 PowerShell**：SSH 包装、端口转发、状态查询

---

## 当前阶段进展

| Demo | 内容 | 状态 |
|---|---|---|
| Demo 0 | 设计收口、skill 适配 | ✅ completed |
| Demo 1 | Book/Chapter 导入 | ✅ completed |
| Demo 2 | AgentRun 长任务追踪 | ✅ completed |
| Demo 3 | 最小问答带引用 | ✅ completed |
| Demo 4 | 最小三栏工作台 | ✅ completed |
| **Demo 5A** | **远程 Linux 服务底座** | **✅ completed** |
| **Demo 5B** | **实体抽取闭环（双端）** | **✅ completed** |
| Demo 6 | 关系/事件/Claim + 图谱增强 | 规划中 |
| Demo 7 | GraphRAG QA + 微调数据准备 | 规划中 |

---

## 安全说明

- **密码、token、私钥禁止写入仓库**。.env 已加入 .gitignore。
- 仓库中只出现：`NB_REMOTE_HOST`、`NB_REMOTE_PORT`、`NB_REMOTE_USER` 和端口配置。
- 敏感信息（`MYSQL_ROOT_PASSWORD`、`NEO4J_AUTH` 等）放在服务器本地 `.env` 中。
- llama-server / MySQL / Neo4j 默认只绑定 127.0.0.1，不暴露到局域网。

---

## 快速开始

### 本地端（Spring Boot）

```powershell
# 连远程开发（需要 SSH tunnel）
.\scripts\remote\nb_tunnel_up.ps1
# IDEA 设置 -Dspring.profiles.active=dev 后启动

# 或本地开发（不需要远程）
cd Novel-Bridge
mvn spring-boot:run
```

### 远端（Linux）

```bash
# 一键启动所有服务
cd ~/novelbridge/deploy/remote
bash nb_up.sh

# 状态检查
bash nb_status.sh
bash nb_healthcheck.sh --json
```

### 上传书籍（触发远端构建）

```powershell
curl.exe -X POST http://localhost:8080/api/book-sources/upload ^
  -F "file=@D:\books\西游记.txt" ^
  -F "title=西游记"
# 自动触发远端 rag-agent 的 /build?source_id=X
```

### 远端同步（远端的 Python 代码传回本地）

```powershell
# 下载远端打包文件
scp <remote-user>@<remote-ip>:/home/wk/novelbridge/sync.tar.gz .

# 一键合并到本地
.\scripts\remote\nb_sync_from_remote.ps1
```
