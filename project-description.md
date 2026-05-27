# NovelBridge  项目描述

> 本文档用于向 AI（如 GPT）描述 NovelBridge 项目，以便获得简历优化、面试准备等指导。
> 按"是什么 → 怎么做的 → 技术决策 → 个人角色 → 项目现状"顺序组织。

---

## 一、项目一句话

NovelBridge 是一个 **API-first 的古典小说阅读分析系统**：从原始文本自动提取实体、关系、事件，建立结构化和向量化知识库，支持带引用溯源的多轮 QA 问答、人物分析、事件追踪和叙事图谱。

---

## 二、项目定位

| 维度 | 说明 |
|------|------|
| 项目类型 | 个人独立开发的开源项目 |
| 目标用户 | 古典文学研究者、AI RAG 路线学习者、对 AI+知识库感兴趣的技术人员 |
| 解决什么问题 | 市面上没有专门针对古典小说的结构化知识库系统，通用 ChatGPT 没有领域深度，且无法保证输出有原文证据支撑 |
| 技术定位 | AI 应用工程 / RAG + Agent 架构 + 混合检索 + 可观测性 |

---

## 三、技术架构

### 整体架构

```
┌─ User (Browser) ──────────────────────────────────────────┐
│  /demo (QA)  /pipeline  /browse  /config  /agent-runs    │
└────────────────────────────┬──────────────────────────────┘
                             │ HTTP REST API
┌─ Python FastAPI ───────────▼──────────────────────────────┐
│  API Layer:    /api/reader-agent/*  /api/v2/*  /api/qa/* │
│  Agent Layer:  IntentDetect → Planner → ToolExecutor     │
│  QA Pipeline:  Rewrite → HybridRetrieval → QualityGate   │
│                → PromptSelect → Generate → Fallback       │
│  Pipeline:     P1(分章) → P2(梗概) → P3(提取) → P4(治理) │
│                → P5(叙事) → P6(索引) → P7(图谱) → P8(导出)│
│  Memory:       MemoryManager(L0/L1/L2) + MySQL 持久化    │
└──────────┬──────────────┬──────────────┬──────────────────┘
           │              │              │
           ▼              ▼              ▼
       MySQL 8        Qdrant 1024d    Neo4j (图)
    (唯一 truth)    (向量检索主力)    (图谱投影)
           │              │
           ▼              ▼
     [SSH Tunnel] ←── manage_server.py
           │
           ▼
    Remote Server (Docker: MySQL/Qdrant/Neo4j + Native: llama-server/Embedding)
```

### 技术栈

| 组件 | 选型 | 选型理由 |
|------|------|---------|
| 后端框架 | Python FastAPI | AI 工程生态成熟，修改-验证循环快 |
| 前端 | Vanilla HTML/CSS/JS | 不引入前端框架依赖，页面积累不多 |
| 数据库 | MySQL 8 (utf8mb4) | 结构化数据的唯一 truth source |
| 向量库 | Qdrant | 独立服务部署，数据不绑定 Python 进程 |
| 图谱库 | Neo4j (可选) | 叙事图谱投影，不作检索 truth |
| 本地模型 | llama-server (Qwen2.5-9B) | 批量提取/草稿/低风险判断 |
| 云端模型 | DeepSeek API | 梗概/审计/改写/高风险判断 |
| 向量模型 | Qwen3-Embedding-0.6B, 1024-dim | 本地可部署，中文古典小说够用 |

### 项目规模

| 度量 | 数值 |
|------|------|
| Python 代码 | ~25,000 行（不含第三方库） |
| API 端点 | ~60+ REST 端点 |
| 数据库表 | 25+ 张 |
| 前端页面 | 7 个（demo/pipeline/browse/search/agent-runs/config/book detail） |
| 内置书籍 | 5 部古典小说（西游记/聊斋/搜神记/山海经/水浒传） |
| 自动化用例 | 37 个 eval 用例 |

---

## 四、核心设计决策

### 4.1 Evidence-first Hybrid RAG，不一步上 GraphRAG

**决策**：检索策略按 Evidence → Entity-aware → Narrative Graph 三阶段演进，当前在第一阶段末尾。

**原因**：
- 古典小说实体别名多（孙悟空=行者=齐天大圣），全局图容易把不同角色混淆
- 关系泛化严重（同门→兄弟？上司/下属→师徒？），LLM 提取的关系质量不够
- 章节动态性：A 在第 10 章是敌人、第 30 章变成盟友，全局图会丢失时间维度

**当前检索策略**：
1. Lexical match（MySQL LIKE）— 精准实体名匹配
2. Dense retrieval（Qdrant 1024-dim cosine）— 语义相似度
3. ChapterFact 结构化检索 — 按实体/事件/关系过滤
4. RRF fusion 合并排名

### 4.2 Python FastAPI + Java Spring Boot 双层架构

**决策**：AI 执行层在 Python，产品 API 壳在 Java，当前 Java 层暂缓开发。

**原因**：
- AI 行为迭代快（prompt 策略、model 切换、retrieval 策略），Python 修改→运行→验证以分钟计
- Java/Spring 从改代码到验证需要更长时间，不适合 AI 层的高频迭代
- 等 AI 层稳定后再做接口对接

### 4.3 ReaderAgent 4 模式

| Mode | 适用场景 | 输出结构 |
|------|---------|---------|
| answer | 事实性问答 | answer + citations |
| analyze | 人物/关系/主题分析 | 结构化分析 (summary/key_points/evidence) |
| trace | 追踪变化/发展/伏笔 | 时间线 items |
| enrich | 发现知识缺口 | KnowledgePatch candidates |

**为什么拆分**：不同任务需要不同的检索策略、prompt 结构和输出 schema。一个 prompt 做所有事会导致 instruction 膨胀、输出不稳定。

### 4.4 Local 9B + DeepSeek 分工

| 任务 | 用谁 | 原因 |
|------|------|------|
| 批量实体提取 | 本地 9B | 吞吐大，成本敏感 |
| 梗概生成 | DeepSeek | 需要全局理解 |
| Query 改写 | DeepSeek | 语义精确要求高 |
| 高风险判断 | DeepSeek | 错误代价大 |

**核心原则**：不把任务绑定到单一 provider。

### 4.5 Retrieval Quality Gate

检索结果必须通过质量门禁（PASS/RETRY/FAIL 决策树），低质量触发重试或拒绝回答。不是"检到什么用什么"。

### 4.6 MemoryManager 三层 + MySQL 持久化

- L0 会话记忆：跨轮次上下文（>10 轮自动 compaction）
- L1 工作记忆：当前分析任务的中间状态
- L2 证据记忆：跨会话证据缓存

三层都通过 MySQL `novel_session_memory` 表持久化，每 60 秒定时刷盘 + 关闭前全量保存 + 启动时自动恢复。

### 4.7 全链路可观测性

每次 AgentRun 记录：run metadata → steps → model calls → tool calls → retrieval traces → citations。Trace Inspector 可逐条回溯。

---

## 五、项目状态

### ✅ 已完成

| 模块 | 状态 | 备注 |
|------|------|------|
| Pipeline P1-P8 | ✅ 完成 | 5 本书全流程可重复跑 |
| QA 问答（answer mode） | ✅ 完成 | Hybrid RAG + Quality Gate + Fallback |
| 多轮对话 | ✅ 完成 | MemoryManager + Reference Resolution |
| Intent Detection | ✅ 完成 | LLM 分类，非硬编码正则 |
| Analyze/Trace/Enrich 模式 | ✅ 完成 | 各自独立的执行路径 |
| Trace Inspector | ✅ 完成 | 全链路可观测 |
| 37 个 Eval 用例 | ✅ 完成 | 自动化评分 |
| 配置管理页面 | ✅ 完成 | 可视化配置所有服务连接 |
| MemoryManager 持久化 | ✅ 完成 | MySQL 三张表 + 定时/关闭保存 |
| 前后端分离 | ✅ 完成 | HTML/CSS/JS 独立文件 |
| SSH 隧道集成 | ✅ 完成 | manage_server.py 一键管理 |
| Pipeline 幂等性 | ✅ 完成 | ON DUPLICATE KEY UPDATE |
| 统一错误模型 | ✅ 完成 | PipelineError + 结构化错误记录 |
| GitHub 发布清理 | ✅ 完成 | 密码清理 + 文档整理 |

### 🚧 待完成

| 模块 | 优先级 | 说明 |
|------|--------|------|
| P3 管线覆盖 analyze/trace/enrich | 高 | 目前只接入了 answer mode |
| 独立 SPA 前端 | 中 | 当前 FastAPI HTML 渲染 |
| Java facade 聚合 | 中 | 产品 API 壳还没对接 |
| Auth/User 系统 | 中 | 目前无用户系统 |
| 生产级部署 | 低 | 单进程，无负载管理 |

---

## 六、个人角色

- **独立开发**：架构设计、后端开发、前端开发、部署运维、文档编写
- **技术选型**：所有技术决策独立完成，每个选型有明确的工程理由
- **代码量**：Python ~25,000 行，Java ~2,000 行，前端 ~3,000 行

---

## 七、项目文件结构（核心）

```
Novel-Bridge/
├── apps/rag-agent/               # Python 后端
│   ├── app/
│   │   ├── api/                  HTTP 路由（~15 个路由模块）
│   │   ├── pipeline/             管线 P1-P8（book_processor/extraction_runner/...）
│   │   ├── qa/                   QA 引擎（retrieval_runner/qa_runner/unified_pipeline）
│   │   ├── reader_agent/         Agent 系统（agent/planner/memory/tools）
│   │   ├── clients/              外部服务客户端（mysql/qdrant/neo4j/llama/deepseek）
│   │   ├── stores/               数据访问层（~15 个 store）
│   │   ├── eval/                 评测系统
│   │   ├── quality/              质量工作流
│   │   └── static/               前端页面
│   └── scripts/                  管理脚本
├── deploy/remote/                Docker 部署
├── docs/                         架构文档（16 篇）
├── schema.sql                    数据库表结构
└── manage_server.py              服务管理
```

---

## 八、用在简历上

### 推荐关键词

- FastAPI / Python / REST API
- RAG / Hybrid Retrieval / Qdrant / Vector Search
- LLM Agent / ReAct / Tool Orchestration
- MySQL / Neo4j / Graph Database
- 可观测性 / Trace Inspector
- 质量门禁 / LLM Eval
- SSH Tunnel / Remote Service Architecture
- Vanilla JS Frontend

### 目标岗位方向

| 方向 | 侧重展示 |
|------|---------|
| AI 应用工程师 | RAG 流水线、Agent 设计、模型编排、质量控制 |
| 后端/架构工程师 | 系统架构、服务拆分、数据持久化、可观测性 |
| 全栈工程师 | 端到端交付、API 设计、前后端联调 |

### 简历撰写建议

1. **不要说"AI Agent"，要说"实现了基于 FastAPI 的 ReaderAgent 多模式执行系统"**
2. **不要只说"用了RAG"，要说"Evidence-first Hybrid RAG，每轮质检+引用，检索不足走 fallback"**
3. **不要只说"个人项目"，要强调"独立完成架构设计到部署全链路"**
4. **诚实区分已完成和计划中**，体现工程判断而非吹嘘
