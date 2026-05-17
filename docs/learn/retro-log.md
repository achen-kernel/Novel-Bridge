# retro-log.md

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
