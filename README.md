# NovelBridge — 智能阅读分析系统

一个本地优先的小说/书籍智能阅读与分析系统。使用本地大模型（llama.cpp）进行结构化知识抽取，
通过 MySQL + Neo4j + 向量库（Chroma）构建知识图谱，支持带原文引用的 GraphRAG 问答。

> 当前阶段：**Demo 5A — 远程服务底座**（已完成）
> 架构定位：Demo 5A 搭建了远程 Linux 服务底座，后续在底座上逐步接入实体抽取、图谱构建和问答。

---

## 整体架构

```
┌─ Windows 本地 ──────────────────────────────────┐
│                                                  │
│  Spring Boot 后端 (:8080)                        │
│    ├─ 业务逻辑：书籍导入、章节切分、状态追踪      │
│    ├─ AgentRun / AgentStep / Citation 审计链      │
│    └─ SSH Tunnel → 远程服务                       │
│                                                  │
│  PowerShell 管理脚本 (scripts/remote/)            │
│    ├─ nb_remote_up.ps1       SSH → 远程启动      │
│    ├─ nb_remote_down.ps1     SSH → 远程停止      │
│    ├─ nb_remote_status.ps1   SSH → 状态查询      │
│    ├─ nb_remote_healthcheck.ps1  SSH → 健康检查   │
│    ├─ nb_tunnel_up.ps1       SSH 端口转发        │
│    └─ nb_tunnel_down.ps1     关闭隧道             │
│                                                  │
└──────────────────────────────────────────────────┘
                         │ SSH Tunnel / HTTP
                         ▼
┌─ Linux 远程 (&lt;remote-ip&gt;) ────────────────────┐
│                                                  │
│  MySQL (:13306)          业务数据存储             │
│  Neo4j (:17474/:17687)   知识图谱                 │
│  Chroma (内嵌)           向量存储                  │
│  llama-server (:18080)   本地 LLM 推理            │
│  rag-agent (:18081)      Python 编排层            │
│                                                  │
│  启动脚本 (deploy/remote/)                        │
│    ├─ nb_up.sh / nb_down.sh   一键启停            │
│    ├─ nb_status.sh / nb_healthcheck.sh  状态检查  │
│    └─ nb_ports.py              端口冲突检测       │
│                                                  │
└──────────────────────────────────────────────────┘
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

### Spring Boot 后端
- **书籍管理**：导入、章节切分、文本清洗
- **长任务追踪**：AgentRun / AgentStep 记录每个异步步骤
- **知识抽取编排**：协作 rag-agent 执行实体抽取流程
- **问答引用**：ChatSession / ChatMessage / Citation 最小问答链路
- **审核流**：候选实体审核、入图确认（Demo 5B+）

### rag-agent (Python)
- **书籍构建管线**：POST /build → 书籍总览分析 → 章节切分（规则+LLM） → 文本分块 → 实体抽取
- **双卡 GPU 推理**：2×RTX 3090，Qwen3.6-35B-A3B MoE 模型，~60-80 tok/s
- **LLM 编排**：构造 Prompt（非 response_format，避开 MoE 模型输出限制） → 调用 llama.cpp
- **结果校验**：JSON 解析、Schema 验证、证据文本校验、重试控制
- **审核流**：候选 approve/reject/edit → 通过后写入 Neo4j（Entity + APPEARS_IN 关系）
- **数据追踪**：每个 chunk 调用记录 model_run，prompt/output/error 全部持久化
- **健康检查**：聚合报告 llama / MySQL / Neo4j / Chroma 状态

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
| **Demo 5B** | **Chunk + 实体抽取闭环** | **✅ completed** |
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

```bash
# 本地启动（不需要远程服务）
cd Novel-Bridge
mvn spring-boot:run
# 浏览器打开 http://localhost:8080

# 远程部署（上传脚本后）
ssh &lt;remote-user&gt;@&lt;remote-ip&gt;
cd ~/novelbridge/deploy/remote
bash nb_up.sh

# 本地连远程开发
.\scripts\remote\nb_tunnel_up.ps1
# IDEA 设置 -Dspring.profiles.active=dev 后启动
```
