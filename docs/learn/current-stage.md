# current-stage.md

阶段 id：demo-5a-remote-foundation
状态：in_progress
循环：demo-first
轮次：Demo 5A

## 功能目标

先完成远程 Linux 服务底座，不直接实现完整 GraphRAG。

Demo 5A 只要求：MySQL、Neo4j、向量库、llama.cpp、Python `rag-agent` 能在远程 Linux 上被一键启动、健康检查，并能被本地 Spring Boot 通过配置访问。

## 本阶段做（已实现）

- ✅ 建立远程部署目录 `deploy/remote/` 和配置模板
- ✅ 设计固定端口在 `ports.env` 中统一管理
- ✅ 创建 Linux Shell 脚本：`nb_up.sh` / `nb_down.sh` / `nb_status.sh` / `nb_healthcheck.sh`
- ✅ 创建 Python 端口检查工具 `nb_ports.py`
- ✅ 创建 Windows PowerShell SSH 包装脚本（6 个）：up/down/status/healthcheck/tunnel-up/tunnel-down
- ✅ 创建最小 `rag-agent` Python FastAPI 服务，含 `/health` 及子路径端点
- ✅ 为 Spring Boot 增加 `RagAgentProperties` + `application.yml` 配置
- ✅ 所有敏感信息通过 `.env` 管理，不写入 tracked 文件（.gitignore 已含 .env）

## 本阶段不做（保持不变）

- 不做关系、事件、Claim 抽取
- 不做完整 GraphRAG QA
- 不做 QLoRA 微调
- 不做外部 wiki 对齐
- 不做复杂图谱可视化
- 不把远程服务器密码、数据库密码、Neo4j 密码或 token 写入 tracked 文件

## mock/临时实现

- 端口先固定，不做随机端口分配 — `ports.env` 集中定义
- 向量库可以先只启动服务和 health check，不要求完成真实检索 — 记为 `mock=true`
- llama.cpp 可以先用一个小模型 smoke test，后续再换 Qwen3.6-35B-A3B — 记为 `mock`
- rag-agent 中 `/extract/entities` 等端点返回 `NOT_IMPLEMENTED`（Demo 5B 实现）

## 已创建的脚本

### deploy/remote/（Linux 服务器侧）
| 文件 | 功能 |
|---|---|
| `ports.env` | 集中端口配置 |
| `services.yaml` | 服务定义元数据 |
| `.env.example` | 环境变量模板（不含密码） |
| `nb_ports.py` | 端口检查工具 |
| `nb_up.sh` | 一键启动所有服务 |
| `nb_down.sh` | 一键停止所有服务 |
| `nb_status.sh` | 服务状态检查 |
| `nb_healthcheck.sh` | 详细健康检查 |
| `README.md` | 部署说明 |

### scripts/remote/（Windows 本地侧）
| 文件 | 功能 |
|---|---|
| `nb_remote_up.ps1` | SSH → nb_up.sh |
| `nb_remote_down.ps1` | SSH → nb_down.sh |
| `nb_remote_status.ps1` | SSH → nb_status.sh |
| `nb_remote_healthcheck.ps1` | SSH → nb_healthcheck.sh |
| `nb_tunnel_up.ps1` | SSH tunnel 到内部端口 |
| `nb_tunnel_down.ps1` | 关闭 SSH tunnel |

### rag-agent/（Python FastAPI）
| 文件 | 功能 |
|---|---|
| `app/main.py` | FastAPI 应用，含 `/health` + `/health/*` |
| `app/__init__.py` | 包初始化 |
| `requirements.txt` | Python 依赖 |
| `.env.example` | rag-agent 环境变量模板 |
| `run.sh` | 启动脚本 |

### Spring Boot 变更
| 文件 | 变更 |
|---|---|
| `common/properties/RagAgentProperties.java` | 新增 `@ConfigurationProperties` |
| `application.yml` | 新增 `novel-bridge.rag-agent.base-url` 默认值 |
| `application-dev.yml` | 覆盖 rag-agent base-url 为远程地址 |

## 验收证据

- ✅ `deploy/remote/` 目录已存在，包含 9 个文件
- ✅ `scripts/remote/` 目录已存在，包含 6 个 PowerShell 脚本
- ✅ `rag-agent/app/main.py` 含 `/health` 聚合端点 + 5 个子端点
- ✅ `nb_healthcheck.sh` 支持 `--json` 输出格式
- ✅ Spring Boot `RagAgentProperties` 可注入 `base-url`
- ✅ 远程服务器 `nb_up.sh` 已执行，MySQL / Neo4j / Chroma embedded / llama-server / rag-agent 均显示 `UP`
- ✅ `docker ps` 已确认 `novelbridge-mysql` 与 `novelbridge-neo4j` 容器运行中
- ✅ llama-server 已通过 `127.0.0.1:18080/v1/models` 返回 Qwen3.6-35B-A3B GGUF 模型信息
- 🔲 需要再执行一次 `nb_down.sh` → `nb_up.sh`，验证从停止状态完整恢复
- 🔲 端口冲突测试（需要在远程执行 `nb_ports.py`）

## 练习决策

- `SKIP-PRACTICE`：本阶段主要是远程部署、端口、health check、服务编排，不适合生成 Java TODO 练习。
- 本阶段学习产物应写入 `retro-log.md` 和 `personal-vibecoding-playbook.md`。

## 风险

- 远程 Linux 环境差异可能导致脚本不可移植
- 模型文件、CUDA、llama.cpp 编译方式可能成为阻塞点
- 如果没有固定端口和 health check，后续调试成本会急剧上升
