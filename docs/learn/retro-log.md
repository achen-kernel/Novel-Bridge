# retro-log.md

## 2026-05-25 - Stage 6C smart planning and model answer quality

### Pitfall: mode selection is a product problem, not a user responsibility

- **Symptom**: `answer` / `analyze` / `trace` / `enrich` are technically meaningful, but a normal user often cannot choose the right one. Their request is usually vague: "看看宋江怎么起来的", "分析一下关系", "这个线索怎么变化".
- **Root cause**: the demo exposed backend execution modes directly as a primary user decision. This is useful for debugging but not ideal for a reader-facing product.
- **Correction**:
  - `/demo` now includes "smart selection";
  - it infers task intent from the question and selected book;
  - it rewrites vague questions into retrieval-friendly prompts;
  - it converts the plan to an existing mode before calling `/api/reader-agent/run`, so the API contract stays unchanged.
- **Lesson**: production UX should be `user asks naturally -> system plans mode/targets -> ReaderAgent executes`. Explicit mode selection should remain as advanced/debug control.

### Pitfall: local 9B answer quality needs a polish/audit layer

- **Observation case**: for "《山海经》如何组织山川地理与神话？", DeepSeek produced a cleaner final answer, while local 9B produced a usable but verbose draft with punctuation defects and broader unsupported claims.
- **What 9B did well**:
  - captured the main "山经/海经 + 地理承载神话" structure;
  - produced strong phrases such as "以山系为骨架，以神话传说为血肉".
- **What 9B did poorly**:
  - repeated ideas;
  - had punctuation artifacts;
  - drifted into broad claims such as "巫书" and "巫师口耳相传" without enough visible evidence.
- **Lesson**: same retrieval context does not imply same final-answer quality. Evaluate retrieval quality and answer-writing quality separately.
- **Follow-up**: add a ReaderAgent answer polish/audit stage that cleans punctuation, compresses repetition, removes internal ids/tags, and flags unsupported broad claims. DeepSeek can be used as final rewrite/audit when configured; local 9B remains useful for low-cost draft and offline demo.

See also: `docs/25-stage-6c-demo-qa-and-planning-lessons.md`.

## 2026-05-21 — 规则系统 + 训练数据飞轮 + 全流程调试

### 背景
完成了规则注册表系统（全局 + 书专属规则）、训练数据采集管线、动态类型词表系统，并在远端 5 本古籍上跑全流程 Pipeline。

### 本次交付
1. **规则注册表** (`app/rules/`): 实体/关系/事件/抽取/分块/合并 6 维度规则，`RuleRegistry` 全局+书规则合并
2. **动态类型词表**: 78 种关系类型 + 90 种事件类型（中文可控词表），归一化映射，DeepSeek 审计
3. **训练数据飞轮**: `TrainingSampleRunner` 采样 + DeepSeek 审核 + 入库 + JSONL 导出
4. **审查修复**: Health 端点、llama-server 连接复用、Qdrant 惰性连接、DeepSeek timeout、nb_up.sh ctx-size、prior_hint 自动生规则

### Pipeline 执行经验

**提取耗时（use_model=True 调 llama-server）:**
- 每 chunk 约 18-60 秒（取决于 chunk 长度和模型负载）
- Book 8 搜神记 35 章: ~60 分钟
- Book 10 水浒传 126 章: ~90 分钟
- 5 本书全量: 6-8 小时

**Phases 4-8 处理时间:**
- Entity Governance: 每本 < 10 秒
- Narrative Build: 每本 < 10 秒
- Index Qdrant: 每本 < 10 秒
- Graph Project: 每本 < 30 秒
- Training Samples: 每本 < 5 秒

### 踩坑记录

1. **FastAPI 422 错误** — POST 端点定义了 Pydantic 请求体（`ProcessRequest`、`ExtractRequest`），空 POST 会报 422。需要传 `{}` 或 `{"use_model": true}`。

2. **远端 MySQL 缺列** — `rules_json` 列不存在导致 `fact_pipeline_runner.py` 500 崩溃。Flyway 迁移未应用到远端 DB，需要手动 ALTER TABLE。

3. **Python httpx 同步阻塞** — `httpx.Client(timeout=43200)` 在等待服务器处理期间不返回，导致 Python 脚本无 log 输出数小时，容易被误判为卡死。**这不是卡顿，是正常等待。** 本质原因是 extract 接口是同步一次性返回所有结果的。

4. **Windows 端口 TIME_WAIT** — 多次启停后，旧连接的 TIME_WAIT 状态阻止新端口绑定（`[Errno 10048]`）。需要等待 30-60 秒或换端口。

5. **PowerShell 内联 Python 字符串引号** — PowerShell 的 `"` 和 Python 的 `"`/`'` 频繁冲突。通过写 `.py` 文件执行可完全避免。

6. **后台进程端口残留** — `Start-Process` + `CreateNoWindow` 启动的进程，旧实例被杀后可能残留 TIME_WAIT。建议用 `netstat -ano | findstr :18082` 确认端口释放。

7. **代码热加载** — uvicorn 默认不 reload，代码修改后必须重启进程。

8. **书顺序影响总耗时** — Book 6 西游记 102 章最大，放在中间跑可能导致 Pipeline 总耗时由最慢的书决定。策略: 最慢的放最后，这样前面的书完成后还能继续跑后续 phase。

### 学习点
- 把长时间运行的 Python 脚本写成 `.py` 文件，用 `Start-Process` 后台启动，避免 PowerShell 超时
- POST body 必须有: FastAPI Pydantic 模型需要 `{}` 最低限度的 body
- 新增列/表后需要手动在远端 DB 执行 ALTER TABLE/CREATE TABLE
- 先跑 1-2 本书验证全流程，再放全量 5 本
- 词表系统的大模型审计应该在抽取完成后单独触发，不阻塞主 Pipeline

### Embedding 踩坑：三层嵌套阻塞

**根因链路：**
1. chunk 最大 21584 bytes（≈7000 汉字），CPU 编码本身需几十秒
2. `model.encode()` 直接写在 async handler 里 → 阻塞 uvicorn 事件循环 → HTTP 响应发不出去
3. PyTorch 在工作线程初始化（`run_in_executor` 内部）→ MKL/OpenMP 线程池混乱 → 16 核跑满 → 系统卡死

**表象：** 服务 health check 正常，但 index 请求无日志无返回，CPU 300-800%。

**修复方案（四管齐下）：**
1. `main.py` — 启动时主线程预加载 embedding 模型
2. `index_runner.py` — 整个 index 流程用 `asyncio.to_thread` 扔到线程池
3. `embedding_client.py` — 同步/异步双版本，>45000 字符截断
4. `rag-agent.service` — `OMP_NUM_THREADS=4` 限制 MKL 线程数

## 2026-05-20 — 远端部署全流程 Pipeline 调试

### 背景
Stage 2-7 的远端 pipeline 已经写完，但在实际跑 Book 6-10 时反复失败。每次修了一个问题又出现新问题，来回折腾了大半天。

### 暴露的问题链

1. **pipeline 脚本写死了 `use_model: false`** → extract 不调用模型，只有规则占位，关系/事件全部为空
2. **修好 `use_model: true` 后** → 模型返回 400，ctx-size=8192 不够
3. **修好 ctx-size=65536 后** → max_tokens=4096 太小，模型输出被截断，JSON 解析失败
4. **修好 max_tokens=16384 后** → temperature=0.3 太低，梗概输出保守
5. **修好 temperature=0.5 后** → 发现 prior_hint prompt 的 `.format()` 与 JSON 花括号冲突

### 根因

**单点修复，缺链路扫描。**

每次只看到眼前报错的那一个参数，没有系统性地检视整个提取链路中所有参数的联动关系。一个完整链路涉及：
```
system_prompt → template_engine → temperature → ctx-size → max_tokens → .env → systemd restart → health_check → end_to_end_test
```

改其中任意一个，都应该检查全部。

### 修复模板

以后修改模型/管线参数时，先执行：
1. 列出完整参数链路
2. 每个参数检查是否要联动调整
3. 改完后重启所有依赖服务
4. 跑一次端到端验证（单本书的一个阶段）再放全量

### 事后排查发现的两个隐藏问题

1. **模型输出 JSON key 名不匹配**：模型输出 `entities`，管线读 `entity_mentions`。84 分钟提取白费。
2. **模型输出 JSON 语法错误**：`Expecting ',' delimiter` — Qwen3.5-9B 自由输出时 JSON 格式不可靠，大量回退到规则模式。

### 修复
- Prompt 指定精确 JSON 结构（字段名 + 嵌套层次）
- 新增 GBNF grammar 文件（`prompts/extraction_output.gbnf`），llama.cpp 层面强制输出合法 JSON
- `chapter_summary` 字段从模型输出抓取并正确传递

### 学习点
- 配置参数从来不是独立的。`ctx-size` 决定 `max_tokens` 的上限，`use_model` 决定是否需要关注 `ctx-size`。
- 修复应该是一次性审查整个链路，而不是见一个修一个。
- LLM 输出 JSON 时，prompt 暗示不够——必须用 grammar 强制约束。
- 数据链路中每个 key 名必须从 prompt → 模型输出 → 解析 → 存储 → 读取 全程一致。
- 成功数 102/102 不代表数据是对的。需要抽样验证实际内容。

---

## 2026-05-19 — Stage 0 重启：从训练管线改为 AI 阅读分析 Agent

### 背景
用户确认远端数据库已删除，项目从头开始。旧约束如 “Java 只能写 `novel_book_source`” 和旧 26 表协议不再保留。项目主线改为 API-first 小说阅读与创作分析 Agent。

### 决策
- 总目标改为：Book → Chapter → Chunk → ChapterFact → Evidence/Citation → Entity Governance → Retrieval QA → Narrative Graph。
- 第一版 RAG 采用 Evidence-first RAG，不直接做 GraphRAG。
- 向量数据库固定为 Qdrant，不再以 Chroma 作为主线候选。
- embedding 模型固定为 `Qwen/Qwen3-Embedding-0.6B`，初始 1024 维，cosine。
- 检索策略固定为 Evidence-first Hybrid RAG：lexical + dense + structured ChapterFact + fusion，后续再加 rerank。
- DeepSeek API 用于概览、校验、审查和高风险判断；本地 9B 用于批量抽取和草稿生成；规则/NLP 做切分、预扫描和 evidence 校验。
- Java 暂定保留为产品后端，但业务代码将重写；Python `rag-agent` 负责 AI worker。
- 内部文本统一 UTF-8，MySQL 使用 `utf8mb4`；输入编码只在 ingestion 解码一次。
- `vibe-learn` 从 practice snapshot 转为 stage harness + route marker + pitfall guard。

### 修改
- 重写 `AGENTS.md`
- 新增 `docs/00-product-goal.md` 到 `docs/09-deployment.md`
- 重写 `schema.sql` 和新增 `deploy/remote/schema.sql`
- 重写 `.opencode/skills/vibe-learn/SKILL.md`
- 重写 `vtl_closing.py`，不再检查 practice
- 新增 `docs/learn/route-markers.md`
- 更新 `docs/learn/current-stage.md` 与 `vtl-state.json`

### 风险
- 旧文档仍保留，后续 agent 必须以新的 `AGENTS.md` 和 `docs/00-09` 为当前权威入口。
- `schema.sql` 和 `deploy/remote/schema.sql` 目前是两份同步副本，后续如果修改需要同时更新或改成单一生成源。
- Java 是否长期保留需要在 Stage 1 前最后确认。

### 学习点
- 对 AI/RAG 项目，practice 副本的学习价值低于 harness 约束、路线标注和质量闸门。
- GraphRAG 应该是通过审核事实的投影，不应该作为第一版事实源。

## 2026-05-18 — 本地端 Schema 简化：只写 novel_book_source 一张表

### 背景
远端调整了数据库策略：Java 上传不再写 `novel_book` + `novel_book_source` 两张表，改为只写 `novel_book_source` 一张表。其余 25+ 张表全由远端 Python 管线管理。

### 修改
- **删除 25 个文件**：`NovelBook`/`NovelChapter`/`NovelChatSession`/`NovelChatMessage`/`NovelCitation` 实体、对应 Mapper、Service、Controller、VO/DTO、Enum
- **简化 `NovelBookSource`**：去掉 `bookId`，`status`→`bookStatus`，`sourceFilename`→`sourceFileName`，新增 `buildStatus`
- **BookSourceMapper**：INSERT/UPDATE 去掉 `book_id`、`created_by`、`updated_by`，字段名对齐远端 `source_file_name`/`book_status`
- **`BookSourceServiceImpl`**：去掉所有 `NovelBook`/`BookMapper` 相关代码，只写 `novel_book_source`
- **`BookOverviewServiceImpl`**：`getBookId()`→`getId()`（表合一后 source 自身 id 即 book 标识）

### 关键决策
1. **远端新建表不带 audit 列**（无 `created_by`/`updated_by`），Java SQL 中去掉对应字段
2. 多文件合并上传（聊斋志异三本合一）继续保留，同样只写 `novel_book_source`
3. `AgentRun`/`AgentStep` 追踪保留，`book_id` 改为 `source.getId()`

### 验证
- `mvn -q compile` 通过

### 踩坑
- `target/` 缓存的旧 `BookMapper.xml` 导致 MyBatis 启动失败，需 `mvn clean`
- 远端表没有 `created_by`/`updated_by` 列，第一次上传报 `Unknown column 'created_by'`

---

## 2026-05-18 — 本地端 Demo 6：Neo4j 查询 + 审核 API 包装 + BookOverview 业务逻辑

### 背景
远程端已跑完西游记 709 chunk 的实体/关系/事件全量抽取（8833 实体、50 万+ 关系、417 事件），但本地端 Java 缺少前端可调用的图谱查询 API、审核包装层和 book_overview 确认流程。

### 本次修改

**新增：Neo4j 只读查询 API（6 个端点）**
- `GET /api/neo4j/books/{bookId}/entities` — 实体列表（支持 type 筛选）
- `GET /api/neo4j/entities/{entityProfileId}` — 实体详情 + 关系
- `GET /api/neo4j/entities/{entityProfileId}/relations` — 实体的所有关系
- `GET /api/neo4j/books/{bookId}/graph` — D3.js 可用的全量图谱数据（nodes + edges）
- `GET /api/neo4j/books/{bookId}/events` — 事件列表
- `GET /api/neo4j/books/{bookId}/stats` — 图统计

技术：Neo4j Java Driver 6.0.5（Spring Boot 4.0.6 管理），直连远程 Neo4j Bolt（SSH Tunnel），`@PostConstruct` 延迟初始化防止 Neo4j 未启动时阻塞应用启动。

**新增：审核 API 包装**
- `POST /api/review/candidates` — 获取候选实体列表（代理远程）
- `POST /api/review/candidates/action` — approve / reject / edit_and_approve（代理远程）
- 模式：纯 HTTP 代理，远程 rag-agent 负责写 entity_profile + Neo4j

**新增：BookOverview 业务逻辑**
- `GET /api/books/sources/{bookSourceId}/overview` — 获取概览（含确认状态）
- `PUT /api/books/sources/{bookSourceId}/overview` — 更新状态（confirm / edit / reject）
- 状态流：PENDING_USER_CONFIRMATION → CONFIRMED / USER_EDITED / REJECTED
- 通过 MyBatis 直连远程 MySQL 读写 `novel_book_source.book_overview` 和 `overview_status`

**被修改的文件**：
- `pom.xml` — +neo4j-java-driver
- `application.yml` / `application-dev.yml` — +Neo4j 连接配置
- `NovelBookSource.java` — +bookOverview、overviewStatus 字段
- `BookSourceMapper.xml` — update SQL 增加 book_overview、overview_status
- `GlobalExceptionHandler.java` — +Neo4jQueryException 处理

### 关键决策
1. **Neo4j 读取方式**：Java 直连 Neo4j Bolt（不需要远程额外暴露只读 API）
2. **审核流程归属**：Java 做 HTTP 代理，远程 rag-agent 负责审批逻辑和 Neo4j 写入
3. **BookOverview 存储**：Java 通过 MyBatis 直读远程 MySQL，不引入独立存储
4. **Jackson 版本**：Spring Boot 4.0.6 使用 Jackson 3.x（包名 `tools.jackson.*` 而非 `com.fasterxml.*`）
5. **Neo4j 驱动初始化**：不阻塞应用启动，连接失败仅 warn 不抛异常

### 依赖远程侧
- `novel_book_source` 表需要 `book_overview` TEXT 列（已有）和 `overview_status` VARCHAR(30) 列
- 远程 rag-agent 需要暴露 `/review/candidates` 的 GET/POST 端点
- Neo4j Event 节点需要 `book_id` 属性（当前 Cypher 使用 `WHERE ev.book_id = $bookId`）

### 踩坑
- Neo4j Java Driver 6.x API 与 5.x 不同：`withConnectionTimeout()` 使用 `(long, TimeUnit)` 而非 `Duration`
- `executeRead()` 回调中不要手动 try-with-resources 关闭 Transaction，由 driver 管理
- `asList()` 在 6.x 中直接返回 Java 原生类型（Map/List），不需要 `Value::asMap` 转换

### 验证
- `mvn -q test` 通过，应用上下文加载成功
- Neo4j 驱动初始化成功（测试环境连接 localhost:17687 验证通过）

---

## 2026-05-16 — vibe-learn 增加 Python 学习线

### 背景
NovelBridge 从 Java/Spring Boot 后端扩展到 `rag-agent`、Chroma、LLM 调用、部署脚本和后续抽取/评测流程。继续把 skill 表达成“Java 项目伴学”会遗漏一条重要成长线：通过真实 AI 项目锻炼 Python 服务和数据处理能力。

### 修改
- `SKILL.md` 增加 `Python Learning Lane`。
- skill 描述从 Java practice 扩展为 Java/Python practice。
- practice 候选加入 typed schema、service call、parsing、chunking、extraction、vector-store、evaluation harness。
- `openai.yaml` 的默认提示同步为 Java/Python practice。
- `vtl-feedback-log.md` 和 `personal-vibecoding-playbook.md` 记录这条新规则。

### 新规则
Python 练习不单独刷语法题，也不强行制造练习。优先从当前 demo 中已经验证过的真实 Python 代码里挑：`rag-agent` endpoint、Pydantic schema、LLM client、Chroma 持久化、文本切片、抽取校验、评测脚本。

## 2026-05-16 — Demo 5A 远程服务实际启动闭环

### 背景
远程 Linux 侧已经进入真实部署调试：MySQL / Neo4j 走 Docker Compose，llama.cpp 走原生 `llama-server`，Chroma 走 `rag-agent` 内嵌持久化。

### 实际结果
- `docker ps` 已确认 `novelbridge-mysql` 与 `novelbridge-neo4j` 均为 `Up`。
- `nb_up.sh` 已能在当前用户下运行 Docker Compose，不再报 Docker socket permission denied。
- 健康检查显示 MySQL、Neo4j、Neo4j-HTTP、Chroma embedded、llama-server、rag-agent 全部 `UP`。
- llama-server 使用 `/v1/models` 检查已正常返回 Qwen3.6-35B-A3B GGUF 模型信息。

### 踩坑
- `.env` 不能只填少量变量。`nb_up.sh` 依赖 `LOG_DIR`、`LLAMA_BIN`、`RAG_AGENT_VENV` 等完整配置。
- Neo4j 密码至少 8 位，过短会导致容器反复重启。
- `.env` 会被 shell `source`，密码应避免反引号、未转义 `$` 等 shell 元字符。
- Docker socket 权限不足时，脚本可能没有真正启动容器，但因为已有服务端口开放，健康检查仍可能显示 `UP`。
- native `llama-server` 应优先检查 `/v1/models`，不要只依赖 `/health`。

### 后续
- 还需要执行一次 `nb_down.sh` → `nb_up.sh`，验证从停止状态完整恢复。
- Spring Boot 还需要连接远程 `rag-agent` 做一次本地到远程链路验证。

## 2026-05-16 — Demo 5A 远程服务底座实现

### 背景
从纯 Spring Boot 开发扩展为跨本地 Windows + 远程 Linux 的服务底座模式。这是项目第一次引入 Python 服务（rag-agent）和远程部署脚本。

### 本次新增
- **deploy/remote/**（9 文件）：`ports.env`、`services.yaml`、`.env.example`、`nb_up.sh`、`nb_down.sh`、`nb_status.sh`、`nb_healthcheck.sh`、`nb_ports.py`、`README.md`
- **scripts/remote/**（6 文件）：PowerShell SSH wrapper（up/down/status/healthcheck/tunnel-up/tunnel-down）
- **rag-agent/**（5 文件）：`app/main.py`（FastAPI）、`requirements.txt`、`.env.example`、`run.sh`
- **Spring Boot**：`RagAgentProperties.java`、`application.yml` 和 `application-dev.yml` 新增 rag-agent base-url 配置

### 关键设计决策
1. **端口集中管理**：所有端口定义在 `deploy/remote/ports.env`，shell 脚本通过 `source` 读取，Python 工具通过文件解析。不允许散落在代码里。
2. **Secret 策略**：密码/私钥路径/DB 密码/Neo4j 密码/API token 必须由本地 `.env` 管理（已 gitignored），仓库中只允许 host/user/port 等非敏感信息。
3. **Mock 边界**：Vector DB 和 llama-server 在 Demo 5A 记为 `mock`，`nb_healthcheck.sh` 和 `rag-agent /health` 的 JSON 输出中明确标记 `"mock": true`。
4. **rag-agent 路由**：rag-agent 的 `/health` 返回聚合状态（llama/mysql/neo4j/vector），每个子服务有独立端点（`/health/llm`、`/health/mysql` 等）。
5. **PowerShell SSH 策略**：本地脚本通过 SSH 调用远程 shell 脚本，而不是在 PowerShell 中重复部署逻辑。SSH tunnel 脚本提供本地调试入口。

### Agent 偏差
- 无重大偏差。总体遵循了 Demo 5A 的范围限定（不实现抽取、不实现 GraphRAG、不做 QA）。

### 验证
- `mvn -q test` 通过（Spring Boot 编译 + 应用上下文加载成功）
- `vtl_closing.py` 全部 GREEN
- 仓库中无明文密码（通过 `rg` 搜索确认）
- `vtl_status.py` 状态正确显示 `demo-5a-remote-foundation`/`in_progress`

### 阻塞项（需要 SSH 连接后验证）
- 远程 `nb_up.sh` 实际执行（需要用户提供 SSH 连接）
- 远程 `nb_healthcheck.sh` 返回 JSON 格式
- `rag-agent` 在远程启动并返回正确 `/health`

### 学习点
- 需求文档第 24-28 节提供了非常详尽的实现蓝图，应该优先遵循。
- PowerShell 和 bash 之间的密码安全传递是需要持续关注的点。
- SSH tunnel 让本地 Spring Boot 可以 "感觉" 连接本地数据库，但需要防 tunnel 断开。

## 2026-05-16 — vibe-learn skill 演化：从练习优先改为工作流与范围控制优先

### 背景
- **项目阶段变化**：Demo 5 已经不再是单一后端功能，而是包含远程 Linux 部署、MySQL、Neo4j、向量库、llama.cpp、Python `rag-agent`、GBNF、人工审核、GraphRAG QA、后续微调等多条技术线。
- **风险**：如果继续把 Demo 5 当成一个大阶段，新开的 agent 很容易一次性实现完整平台，导致范围失控、服务难以验证、文档和代码同步困难。
- **用户判断**：`vibe-learn` 不应该把“挑练习代码/生成练习副本”作为核心价值。更重要的是帮助新人形成 vibe coding 工作流：拆 demo、控范围、做证据、记录决策、沉淀个人方法。

### 原 skill 暴露的问题
- **练习机制过强**：`vtl_closing.py` 原本把 `@VTL-PRACTICE` 作为硬检查，容易迫使 agent 在部署、Prompt、GBNF、服务编排这类阶段硬找低价值 Java 练习代码。
- **缺少范围切分规则**：`SKILL.md` 虽然强调 demo-first，但没有明确说明“一个 Demo 同时包含部署、模型、图谱、向量库、前端、QA、微调时必须拆分”。
- **AGENTS.md 入口过旧**：仍把目标描述成早期 `Book/Chapter/Chunk -> Chat/Citation`，没有提示 Demo 5 已拆成 5A/5B/6/7。
- **状态文件过旧**：`vtl-state.json` 和 `current-stage.md` 还停在旧 Demo 1/2 语境，新 agent 会按旧阶段开工。

### 本次修改
- **`.opencode/skills/vibe-learn/SKILL.md`**
  - frontmatter description 增加 Python service、local LLM、scope control。
  - Default Loop 第 7 步从 `Practice` 改为 `Practice decision`。
  - 新增 `Scope Slicing Rule`：当一个 demo 同时包含远程部署、数据库、模型推理、图谱/向量库、前端审核、在线 QA、微调评估等多个关注点时，必须拆成可验收子阶段。
  - 明确 infrastructure/deployment/planning/prompt-only 阶段可以跳过练习，但必须记录原因。
- **`.opencode/skills/vibe-learn/scripts/vtl_closing.py`**
  - 检查项从 `practice_markers` 改成 `practice_decision`。
  - 允许两种通过方式：存在 `@VTL-PRACTICE` 标记，或 `practice-plan.md` 记录 `SKIP-PRACTICE`。
  - 避免 agent 为通过 closing 检查而制造低价值练习。
- **`.opencode/skills/vibe-learn/agents/openai.yaml`**
  - default prompt 改为强调小 demo、拆分 oversized work、retros、可选 practice snapshots。
- **`AGENTS.md`**
  - Read First 加入 `novel_bridge_demo_5_gbnf_开发需求文档_v_0_1.md`。
  - Current Direction 改为 Demo 5A/5B/6/7 分层。
  - 加入 secrets 规则：不得把服务器密码、数据库密码、Neo4j 密码、token 写入 tracked 文件。
  - closing checklist 改为 `practice_decision`。
- **`docs/learn/demo-plan.md`**
  - Demo 5 拆成 Demo 5A 远程服务底座、Demo 5B 实体抽取闭环、Demo 6 图谱抽取增强、Demo 7 GraphRAG QA 与数据沉淀。
- **`docs/learn/practice-plan.md`**
  - 增加 `SKIP-PRACTICE` 机制。
  - Demo 5A/5B 先记录跳过练习原因，后续等稳定代码出现后再挑选高价值方法。
- **`docs/learn/current-stage.md` 与 `docs/learn/vtl-state.json`**
  - 当前阶段同步为 `demo-5a-remote-foundation`。
  - 明确本阶段只做远程服务底座和 health check，不做完整 GraphRAG。
- **`docs/learn/vtl-feedback-log.md`**
  - 记录本次 skill 演化候选：Demo 5 范围扩张时，skill 缺少 scope slicing 和 practice skip 规则。

### 新的执行规则
- 新 agent 进入项目时，先读 `AGENTS.md`、`vibe-learn/SKILL.md`、`current-stage.md`、`demo-plan.md`、Demo 5 需求文档。
- 如果需求文档描述的是最终系统，不代表当前 demo 要全部实现。
- Demo 5A 只做远程服务底座：部署目录、固定端口、启动脚本、health check、Spring Boot 配置入口、secrets 不落盘。
- Demo 5B 才做实体抽取闭环：chunk、model_run、entity candidate、review、Neo4j 最小写入。
- Demo 6 才做关系、事件、Claim 和图谱增强。
- Demo 7 才做 GraphRAG QA、评测和微调数据导出。
- 每轮 closing 时，practice 可以是 `@VTL-PRACTICE`，也可以是 `SKIP-PRACTICE`。跳过必须写清楚原因和后续补偿。

### 验证
- `quick_validate.py D:\Novel-Bridge\.opencode\skills\vibe-learn` 通过，输出 `Skill is valid!`
- `python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json` 通过，当前阶段为 `demo-5a-remote-foundation`
- `python .opencode\skills\vibe-learn\scripts\vtl_status.py --root . --json` 正确读取新阶段和新 `current-stage.md`

### 学习点
- 伴学 skill 的核心价值不是自动生成练习，而是把 agent 的行为限制在正确工作流里。
- 对大型 AI/RAG 项目，最关键的学习能力是“拆阶段、控范围、定义验收、保存证据、复盘偏差”。
- 练习代码应该是高价值副产物，不应该成为每轮 demo 的强制负担。
- 脚本化 harness 要允许“明确跳过”，否则 agent 会为了满足检查项制造无意义产物。

## 2026-05-14 — 项目结构重组（common/pojo/server 对齐苍穹外卖）

### 决策：controller/mapper/service/handler 统一搬到 server/ 下
- **背景**：项目结构未对齐参考模板（苍穹外卖），controller/mapper/service 在根包下，handler 在 common 下
- **方案**：
  - `controller/` → `server/controller/`
  - `mapper/` → `server/mapper/`
  - `service/` → `server/service/` + `server/service/impl/`
  - `common/handler/` → `server/handler/`
  - common/ + pojo/ 保持不变
- **影响**：16 个文件 package 变更，需更新 @MapperScan、BookMapper.xml namespace
- **验证**：mvn test 通过

### Practice 版本优化：一键启动 + 自动配置 + practice 分支
- **问题**：practice 副本缺少 run.bat、IDEA 不识别 Maven、每次重生成后 IDEA 需重配
- **旧方案（已废弃）**：目录复制（每次删整个目录 → .idea/ 丢失 → IDEA 需重配 JDK + Maven）
- **新方案**：
  - 使用 **git practice 分支**（`git branch practice-xx && git worktree add`）替代目录复制
  - `.idea/` 仅创建一次永久保留
  - `vtl_practice.py` 新增 `--inplace` 参数：跳过 copy_tree，仅转换标记 + 生成辅助文件
- **更新流程**：`cd ../practice-dir && git merge master && python vtl_practice.py --target . --inplace`
- **验证**：100 回 book 导入 + 问答 API 可用；mvn test 通过

## 2026-05-14 — JPA → MyBatis 迁移

### 决策：Spring Data JPA → MyBatis 4.0.0
- **原因**：用户要求使用 MyBatis（带 SQL 映射）+ 后续再用 MyBatis-Plus
- **删除**：`spring-boot-starter-data-jpa`、`spring-boot-starter-data-redis`
- **新增**：`mybatis-spring-boot-starter:4.0.0`
- **配置**：`@MapperScan`、`mybatis.mapper-locations`、`map-underscore-to-camel-case`
- **Entity 变化**：所有实体剥离 JPA 注解，改为纯 POJO + `extends BaseEntity`
- **BaseEntity 变化**：移除所有 JPA 注解（`@MappedSuperclass`、`@Id`、`@GeneratedValue`、`@Column`、`@PrePersist`、`@PreUpdate`）
- **Mapper 变化**：`extends JpaRepository` → `@Mapper` + `@Insert` / `@Select` / `@Update`
- **XML 映射**：`BookMapper.xml` 演示 XML 动态 SQL 用法（`<set>` + `<if>`）
- **schema**：`src/main/resources/schema.sql` 定义所有表（11 张，含预留表）
- **配置**：移除 JPA 相关配置，添加 MyBatis 配置，启用 SQL 初始化

### Bug：mybatis-spring-boot-starter 版本兼容性
- **现象**：3.0.4 和 3.0.5 报 `Property 'sqlSessionFactory' or 'sqlSessionTemplate' are required`
- **根因**：Spring Boot 4.0.6 需要 `mybatis-spring-boot-starter:4.0.0`
- **修复**：版本升至 4.0.0，测试通过
- **教训**：Spring Boot 大版本升级时，第三方 starter 也需要对应大版本

## 2026-05-14 — Architecture hardening (Post-Demo 2)

### 新增：统一响应模型 + 异常体系
- **新增**：`common/result/Result<T>` 统一 API 响应（code=1/0, msg, data）
- **新增**：`common/exception/BaseException` 业务异常基类
- **新增**：`common/handler/GlobalExceptionHandler` 全局异常处理器
- **新增**：`common/properties/BooksProperties` — `@ConfigurationProperties` 替代 `@Value` 硬编码
- **改造**：BookController 从 `ResponseEntity<VO>` 改为 `Result<VO>`
- **改造**：BookServiceImpl 从 `@Value` 注入改为 `BooksProperties` 注入
- **改造**：NovelBridgeApplication 增加 `@ConfigurationPropertiesScan`
- **学习点**：@Value 适合简单取值，@ConfigurationProperties 适合配置集中管理、类型安全、IDE 自动补全
- **学习点**：RestControllerAdvice 的异常处理优先级：子类优先。BaseException → IllegalArgumentException → MethodArgumentNotValidException → Exception

## 2026-05-14 — Demo 1 ~ 2

### Bug: PowerShell curl 导致 JSON 解析失败
- **现象**：`JSON parse error: Unexpected character ('f'...)`，POST 请求体被截断
- **根因**：PowerShell 的 `curl` 别名在反引号换行时损坏了 JSON
- **修复**：改用 `Invoke-RestMethod` 或 Apifox
- **教训**：shell 的 curl 实现在不同平台行为不同，怀疑时先试 `Invoke-RestMethod`

### 决策：application.properties → application.yml
- **原因**：单文件不够分层，不便区分 dev/prod 配置
- **方案**：拆为 `application.yml`（公共）+ `application-dev.yml`（开发环境）
- **额外**：顺便禁用了 Redis 自动连接（当前阶段不需要）

### 决策：.reasonix 废弃，迁移到 .opencode
- **原因**：项目从 Reasonix agent 切换到 OpenCode agent，两套 skill 副本不一致
- **方案**：AGENTS.md、adapter、state 所有路径改为 `.opencode/skills/vibe-learn`
- **影响**：`.reasonix/` 已加入 gitignore，不再追踪

### 决策：删除 Novel-Bridge/ 内层的冗余文件
- **删除**：`mvnw`、`mvnw.cmd`、`.mvn/`、内层 `.gitignore`、`.gitattributes`
- **原因**：使用本地 Maven，wrapper 文件和冗余配置多余
- **教训**：Spring Initializr 生成的模板文件不是都需要保留

### Agent 偏差：Demo 1 完成后跳过 Retro/Practice/Skill
- **现象**：完成了代码、验证了 DB，但忘记标记 `@VTL-PRACTICE`、忘记写 retro、忘记更新 playbook
- **根因**：orchestrator 的"执行→验证"循环和 vibe-learn 的 8 步循环没有挂钩点
- **修正**：在 AGENTS.md 补充 "vibe-learn 收尾检查清单"

## 2026-05-13 — 项目重启

### 决策：从按功能分包改为三层包结构
- **背景**：第一版代码按功能分包（user/、book/、agent/…），共 57 个文件
- **问题**：作为学习项目，按功能分包看不到每层的职责边界，不适合初学者
- **决策**：清空旧代码，改为 common / controller / pojo / server 三层结构
- **影响**：旧 57 文件已删除，从空白骨架重新开始，分 9 轮渐进实现
- **教训**：学习项目一开始就应该用清晰的分层结构

### 决策：Git 仓库位置
- **第一版**：git 建在 Novel-Bridge/ 子目录内，data/ 和 docs/learn/ 在外
- **纠正**：删掉子目录 git，在项目根目录 D:\Novel-Bridge 重新 init
- **原因**：根目录涵盖了后端、数据、文档、skill 所有内容

## 2026-05-12 — 第一次尝试

### Bug: MySQL Connector/J 9.x 不支持 utf8mb4 编码名
- **现象**：`Unsupported character encoding 'utf8mb4'`
- **修复**：JDBC URL 中 `characterEncoding=utf8mb4` → `characterEncoding=UTF-8`
- **教训**：新 JDBC 驱动对字符集编码名更严格

### 决策：EntityProfile + significance
- **原因**：区分主角与次要角色，为 v2 聚合铺路
- **字段**：significance 枚举 MAJOR / SUPPORTING / MINOR / CAMEO
- **范围**：v1 只建表 + CRUD，不做跨章聚合

### 决策：单一数据库 novel_bridge + book_id 归属
- **原因**：连接管理简单、支持后续多书问答、建表脚本可复用
# 2026-05-24 - Stage 3 ReaderAgent answer demo

## Completed

- `POST /api/reader-agent/run` real smoke test passed with `RESPONDED`, non-empty answer, and 6 citations.
- `GET /api/reader-agent/runs/{run_id}/trace` returned run, steps, and traces.
- `novel_retrieval_trace` is now part of root schema, remote schema, and Java Flyway migration `V7__add_retrieval_trace.sql`.
- Qwen3.5 native `llama-server` must start with explicit chat template, `--jinja`, and `--reasoning off`; otherwise chat completion may return empty `message.content`.

## Follow-up

- `PreprocessAgent` still needs action wrappers around existing pipeline.
- `KnowledgePatch` remains propose/review skeleton only.
- ReaderAgent model-call recording is not fully wired yet; current answer mode records run/steps/trace.
## 2026-05-25 - Stage 6C demo presentation correction

### Pitfall: evidence output is not a reader answer

- **Symptom**: `analyze` and `trace` demo results looked like internal retrieval output. The page showed entity type labels, relation records, chunk excerpts, and chunk ids as if they were chapters.
- **Root cause**: minimal deterministic modes treated retrieved evidence excerpts as final summaries. The frontend then rendered those summaries directly, so the demo exposed RAG plumbing instead of model analysis.
- **Correction**:
  - evidence remains mandatory, but it is now analysis input, not the primary user-facing answer;
  - `trace` timeline summaries are concise relation-state/context summaries, while raw excerpts stay in evidence/debug views;
  - `analyze` now attempts model synthesis from compressed evidence and structured clues, with rule-based fallback;
  - answer prompt was relaxed from a rigid 3-5 sentence template to a natural response contract.
- **Lesson**: for portfolio demos, evidence-first does not mean evidence-as-answer. The product route should be `retrieve evidence -> model analyzes evidence -> validate answer has support -> expose citations/debug separately`.

## 2026-05-26 — Stage 6H.1 orchestration trace closure

### Finding: agent had structure but not runtime wiring

Another model review found 6 specific issues after the first fix round:
1. ReaderRequest had no `tool_sequence` field → /run couldn't receive external plan
2. ReaderAgent didn't create orchestration run → tool calls had no shared run_id
3. ToolExecutor had no tool_call_store → orchestrator tool calls not persisted to DB
4. audit ran twice (once empty, once with answer)
5. shared_run_id was always None (tried to capture from mode output but captured too late)
6. No end-to-end test for tool_sequence → audit → polish pipeline

### Fixes applied

| Fix | What | File |
|-----|------|------|
| ReaderRequest.tool_sequence | Added optional `list[ToolCallStep]` field | `schemas.py` |
| /run passes tool_sequence | `agent.run(req, tool_sequence=req.tool_sequence)` | `reader_agent.py` |
| Orchestration run | ReaderAgent creates top-level AgentRun with mode="orchestrator" | `agent.py` |
| MysqlToolCallStore inject | ReaderAgent.__init__ creates store when conn available | `agent.py` |
| Single audit | audit step injects answer from accumulated, runs once | `agent.py` |
| run_id at start | accumulated["run_id"] = orchestration_run_id (set before loop) | `agent.py` |

### Lesson
Review cycles work. The first round fixed visible bugs (field loss, no polish). The second round fixed the deeper structural issues (no orchestration run, no tool call store). The pattern of "another model reviews → finds wiring gaps → fixes them" is effective for runtime closure. Add this to playbook.

## 2026-05-26 — Stage 6H runtime closure fixes

### Pitfall: planner.tool_sequence existed but was not consumed by /run

- **Symptom**: another model review found that even though `plan()` correctly produced `tool_sequence`, the `/api/reader-agent/run` endpoint never actually used it. It relied on `_default_sequence()` which was functional but dropped most fields from the ReaderRequest.
- **Root cause**: the codebase had the structural pattern (ToolCallStep, tool_sequence in PlanResponse) but the `reader_agent_run` API endpoint didn't bridge the gap. It accepted a `ReaderRequest` which has no `tool_sequence` field, and `ReaderAgent.run()` only used `tool_sequence` when explicitly passed.
- **Fix**: `ReaderAgent.run()` now calls `reader_plan()` internally when `tool_sequence is None`. This ensures the plan is always consumed.
- **Lesson**: orchestration patterns must have end-to-end tests. Schema/registry tests are not enough — you need to verify that data flows from API endpoint → planner → agent → tools → response.

### Fix list

| Fix | File | Change |
|-----|------|--------|
| #1 tool_sequence consumption | agent.py | run() calls reader_plan() when no tool_sequence |
| #2 field loss | agent.py | _default_sequence() passes all ReaderRequest fields |
| #3 hybrid_search → memory | agent.py | items → L2 EvidenceMemory |
| #4 audit receives answer | agent.py | audit tool injects accumulated answer, writes back polished |
| #5 tool call trace | agent.py | ToolExecutor gets run_id/step_id |
| #6 entity_name passthrough | tools.py | hybrid_search tool passes entity_name to RetrievalRunner |

## 2026-05-26 — Provider comparison eval + prompt engineering

### Eval 核心发现

运行 `test_provider_comparison.py` 对比 Local 9B vs DeepSeek，37 个 eval cases：

- **Local 9B**: 31/37 PASS (83.8%), avg 10s/case, avg ~715 chars, avg ~4.2 citations
- **DeepSeek**: 21/29 PASS (72.4%), avg 7s/case, avg ~410 chars, avg ~2.6 citations

### 主要结论

1. **86% 的 FAIL 原因是检索结果为 0，不是模型质量**。两个 provider 共享同一套检索系统，当检索失败时都 FAIL。
2. **唯一双 FAIL 主题：崂山道士道理** — 知识库完全缺失该主题。
3. **西游主题整体薄弱**：Local 9B 有 3 个西游 FAIL，西游记 102 章但某些主题检索缺失。
4. **水浒角色别名导致检索失败**：宋江(及时雨)、鲁智深(鲁提辖)等别名未被检索覆盖。

### 工程改动

基于分析做了 3 项改动：
1. **Retrieval Quality Gate** — QaRunner 在 `contexts` 为空时直接返回 INSUFFICIENT_EVIDENCE，节省一次无效 LLM 调用。
2. **Provider-specific prompts** — Local 9B prompt 加强"每个论断必须引用"约束；DeepSeek prompt 增加枚举性问题要求和最低长度指导。
3. **Provider-specific answer style contract** — 各自独立，不再共享同一套输出约束。

### 记录

- `docs/provider-comparison-analysis.md` — 完整分析报告
- `apps/rag-agent/analysis_result.md` — DeepSeek 的分析原始输出
- `scripts/test/test_provider_comparison.py` — 对比 eval 脚本
- `scripts/test/analyze_provider_comparison.py` — DeepSeek 分析脚本

## 2026-05-25 — Stage 6E ReaderAgent planner and answer polish

### Decision: backend planner replaces frontend-only smart selection

- **Symptom**: `/demo` already had smart mode selection, but it was pure JavaScript. The JS version worked, but duplicated entity knowledge, lacked confidence scoring, was untestable offline, and was not reusable by other clients.
- **Change**: Added `POST /api/reader-agent/plan` with the same deterministic logic in Python. Demo JS now calls the backend planner, with local JS rules as fallback.
- **Result**: planner has 18 unit tests, confidence scores, warnings, and a `request_patch` contract.
- **Lesson**: when frontend and backend share similar business logic (mode inference, entity matching), put the canonical version in the backend where it can be tested and reused. Keep frontend rules only as fallback.

### Decision: answer polish as pure functions

- **Why**: both local 9B and DeepSeek outputs can contain `<cite>` tags, chunk IDs, and punctuation artifacts. These are formatting issues, not content issues, and should be cleaned deterministically without model calls.
- **Implementation**: `answer_polish.py` provides `strip_citation_tags`, `strip_internal_ids`, `clean_duplicate_punctuation`, `collapse_whitespace`, and the composite `polish()` function.
- **Status**: functions exist and pass 12 tests, but are not yet wired into mode runners (deferred to Stage 6G).
- **Lesson**: separating cleanup from model generation keeps the cleanup logic testable and provider-independent. Integration into the execution pipeline can happen in a later stage.

## 2026-05-25 — Stage 6F/6G session memory and answer polish complete

### Decision: in-memory session store for demo

- **Why**: DB-backed session (MySQL) would add schema changes, migration scripts, and store implementation overhead. The demo already has MySQL connection issues during long LLM calls. In-memory avoids that.
- **Trade-off**: sessions are lost on server restart. Acceptable for demo — sessions are numbered sequences, not user accounts.
- **Implementation**: async `asyncio.Lock` around a `dict[int, SessionState]`. Each session stores turn history, current target, and evidence IDs.

### Decision: reference resolver is deterministic, not model-based

- **Why**: pronoun resolution in a novel domain ("他" could be any of 20+ characters) is genuinely complex if done with full NLP. But for demo purposes, "他" always resolves to `session.current_target_name` — which is exactly what the user meant because they just asked about that target.
- **Result**: the resolver handles "他"/"她"/"他们", relation refs ("这关系"), trace refs ("这条线索"), evidence refs ("这些证据"), and mode-switch requests ("换成时间线").
- **What it doesn't handle**: ambiguous pronouns in multi-character discussions. A model-based planner could do this later.

### Decision: answer polish in agent.py post_process, not per-mode

- **Previous approach**: each mode runner would need to call `polish()` individually. If a new mode is added, polish might be forgotten.
- **New approach**: `_post_process()` in `agent.py` wraps every mode runner. All answers get formatted cleanup + audit notes.
- **Provider awareness**: `polish(text, "local")` does full cleanup (internal IDs, punctuation, whitespace). `polish(text, "deepseek")` skips internal ID removal because DeepSeek outputs are cleaner.

### Decision: broad claim detection is pattern-based

- **Patterns**: "古代百科全书", "最重要的", "毫无疑问", "巅峰之作", etc.
- **Limitation**: pattern-based detection has false positives and misses novel broad claims. But it's better than nothing — at least the system can flag "这是毫无疑问最重要的作品" without any evidence support.
- **Future**: a model-based audit pass (DeepSeek verifying each claim against evidence) would be more accurate but slower and costlier.

## 2026-05-25 — Stage 6E ReaderAgent planner and answer polish

### Decision: backend planner replaces frontend-only smart selection

- **Symptom**: test case 7 ("追踪宋江成为梁山核心的关键线索") returned `target_name="宋江, 梁山"` because both entities appear in the question. The test initially expected just `"宋江"`.
- **Root cause**: the planner correctly identifies all known targets, not just the primary target. "梁山" is a known setting in book 10.
- **Correction**: adjusted the test expectation to accept `"宋江" in target_name`. The planner behavior (capture all known entities) is correct — the caller should decide which target is primary.
- **Lesson**: entity target collection should return all matches; narrowing to a primary target is a downstream concern.


## 2026-05-26 — Demo 前端修复 + reference resolver 增强

### Bug: Health check 中 Embedding 的 HTML id 不匹配
- **症状**: /health/embedding 返回 200 OK，但前端 Embedding 点一直红色
- **根因**: HTML id 是 h-emb，JS 索引却是 h-embedding → 查不到元素 → catch → 标红
- **修复**: hnames 改为 [[html_id, api_path], ...] 双列格式

### Bug: 详情面板无法关闭
- **症状**: 点击回答的「详情」按钮后右侧面板弹出，没有关闭按钮
- **修复**: 面板头部加 ✕ 关闭按钮

### Bug: 参考问题错字
- **症状**: 搜神记问题列表有「报效观念」
- **修复**: 改为「报应观念」

### Bug: 会话记忆元问题不处理
- **症状**: 用户问「我刚问的是什么」，系统不记得上一轮对话
- **根因**: reference_resolver.py 只处理代词和关系引用，不处理「刚才」「刚问」等元引用
- **修复**: 增强 resolver，检测「刚问」「我刚才」「我上一轮」等模式，替换为带 session context 的检索问题

## 2026-05-26 — MemoryManager runtime wiring + reference resolver 增强

### Wiring: MemoryManager 接入 unified_pipeline
MemoryManager 之前是孤岛。unified_pipeline 不接收 MemoryManager，不记录 session。
改动: run_pipeline() 现在接收 memory_manager，每轮自动: 1.重置 L1/L2 2.写 L1 plan 3.QueryRewriter 从 L0 取最近3轮 4.完成后 record_turn 5.超过10轮自动压缩

### Reference resolver 增强
新增代词: 这位/该人; 关系: 他俩/他们俩; 线索: 这条线/这个走向; 回答: 你的回答/你刚才说的; 证据: 你引用的; 模式: 换一种说法/换个角度/继续说/展开说说; 前序问题: 我刚问/我刚刚问/我问的是什么/我上一轮/刚才的问题/之前的问题/第一个问题/最开始的问题

### 改动文件
- unified_pipeline.py — 新增 MemoryManager 参数 + 会话窗口管理
- reader_agent.py — /run 传递 MemoryManager
- planner.py — session context 使用 MemoryManager L0
- reference_resolver.py — 新增 20+ 引用模式

## 2026-05-27 — Pipeline 重跑 + 背景任务 + 流水线前端（7 个坑）

### 坑 1：CRLF 导致 chunker 段落检测完全失效

**症状**：搜神记只有 85 chunks（预期 400+），聊斋 471（预期 1500+），所有书的 chunk 数偏低。

**根因**：`chunker.py` 按 `\n\n` 切段落，但 MySQL 存的是 `\r\n`（Windows CRLF）。  
`\r\n\r\n` ≠ `\n\n` → 整章变成一个"段落" → `smart_split_text` 在 50% 中点硬切 → chunk 内容不连贯。

**修复**：`chunk_chapter()` 入口处加 `chapter_text.replace('\r\n', '\n').replace('\r', '\n')`。

**效果**：聊斋 471→1511 chunks，搜神记 85→147 chunks。

**教训**：字符串处理的边界问题（换行符/编码/空格）在 pipeline 中影响巨大且静默。遇到数据量异常先检查数据本身的格式。

### 坑 2：规则回退硬编码空列表，模型不可用时关系/事件数据全丢

**症状**：`use_model=False` 时实体提取正常但关系/事件为 0。

**根因**：`extraction_runner.py:_rule_extract()` 中 `relation_mentions = []`、`event_mentions = []` 是硬编码占位符，从未实现。

**修复**：添加启发式规则——同段共现实体 + 关系动词匹配（25 个关系动词：是/有/拜/率/居 等）+ 事件关键词（20 个动作词：打/战/杀/救 等）。

**教训**：所有 fallback 路径必须等价于主路径的能力子集。硬编码空列表不是 fallback，是静默丢数据。

### 坑 3：Neo4j 全局清除——`clear_all()` 删了所有书

**症状**：多本书运行时，P7 投影清除了所有书的图数据。

**根因**：`graph_projector.py:31` 调用 `neo4j_client.clear_all()` 执行 `MATCH (n) DETACH DELETE n`，无 book_id 过滤。

**修复**：所有节点创建时加 `book_id` 属性，新增 `clear_book(book_id)` 方法，`project_book()` 改用 `clear_book()`。

**教训**：全局销毁操作（DROP TABLE / DELETE ALL / clear_all）必须显式声明危险，且默认不使用。多租户（多书）架构必须按 scope 操作。

### 坑 4：MySQL 共享连接被消费者 close() 导致下游崩溃

**症状**：P2 "Already closed" 错误，P3 "KeyError: 0"。

**根因**：`MysqlClient.connect()` 返回的是**共享单例连接**。P1 runner 在 `finally` 里调 `conn.close()` 关闭了它。`_is_connected()` 检测到连接断开后重建，但重建时 `pymysql` 内部状态混乱导致 "Already closed"。

**修复**：彻底去掉所有 `conn.close()` 调用。`MysqlClient` 管理自己的连接池，消费者只使用不销毁。

**教训**：共享资源的生命周期管理者只能有一个。谁创建谁销毁，消费者只读不关。对数据库连接这种频繁使用的共享资源，加文档明确标注"不要 close()"。

### 坑 5：`esc()` 函数缺失 — 流水线页面一直"加载中"，定位耗时>1h

**症状**：`/pipeline` 页面显示"加载中"，Ctrl+F5、无痕窗口都无法解决。

**根因**：`frontend.py` 的流水线 HTML 是独立模板，从 demo.py 复制时漏掉了 `function esc()`。`renderPipeline()` 中 64 处调用 `esc()` 全部失败，但页面停留在"加载中"初始状态，无任何错误提示（页面没有 `window.onerror` 处理器）。

**定位过程**：
1. 怀疑服务器挂了 → 健康检查通过 ✅
2. 怀疑 API 挂了 → curl 返回 200 ✅
3. 怀疑 JS 语法错误 → python 检查大括号平衡 ✅
4. 怀疑浏览器缓存 → 无痕模式 → 依然失败 ❌
5. 最终用户开 F12 Console 看到 "esc is not defined" → 1 秒定位

**如果一开始就开 F12 Console**：定位时间从 >1h 降到 5s。

**教训**：
- 前端不加载的第一步是 **F12 → Console**，不是问"服务器挂了没"
- 创建新页面时必须确认所有 helper 函数完整
- 页面应有 `window.onerror` 显示浮层错误
- 调试协议：浏览器 → Console → Network → 再问后端

### 坑 6：JS 同名函数在多次编辑中静默覆盖

**症状**：自动刷新只执行 `setInterval`，不更新按钮进度状态。

**根因**：`frontend.py` 的 JS 尾部出现了两个 `async function refreshStatus()` —— 第一次加的是完整实现，第二次编辑时又加了一个 `async function refreshStatus(){setInterval(...)}`。第二个定义覆盖了第一个。

JS 允许同名函数重复定义，不报错，最后一个生效。文件经过多次 edit 操作，每次都是在字符串中追加，产生了重复。

**修复**：删掉第二个函数定义，把 `setInterval` 放在函数体外独立调用。

**教训**：在 f-string 模板中多次编辑 JS 后，必须检查有无残留的函数/变量重复定义。用 `grep "async function"` 快速检查。

### 坑 7：热重载在快速连续修改时漏检文件变更

**症状**：代码已经修正，curl 检验 API 返回 200，但浏览器永远拿到旧 HTML。

**根因**：`uvicorn --reload` 的 WatchFiles 依赖文件系统事件，在多个文件快速连续修改时可能遗漏事件。`__pycache__` 中的 `.pyc` 缓存了旧代码，重启后也不一定刷新。

**修复**：显式删除 `__pycache__` 再杀进程重启，而不是依赖热重载。

**教训**：热重载是开发便利，不是可靠部署。修改代码后如果观察到的行为与代码不符，执行：
1. `Remove-Item -Recurse -Force __pycache__`
2. 杀进程重启
3. curl 验证输出

