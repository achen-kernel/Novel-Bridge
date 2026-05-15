# current-stage.md

阶段 id：demo-1-book-import
状态：completed
循环：demo-first
轮次：demo 1

## 功能目标

导入样例书（西游记.txt）并通过简单正则切分为 100 回章节，持久化到 MySQL。

## 本阶段做

- 创建 BaseEntity（MappedSuperclass，含 id/createdAt/updatedAt/createdBy/updatedBy）
- 创建 NovelBook + NovelChapter JPA 实体
- 创建 BookRepository + ChapterRepository
- 实现 ChapterSplitter（中文数字转 int + 正则 `第X回` 拆分）
- 实现 BookService（createBook + buildBook 两步 API）
- 实现 BookController（POST /api/books + POST /api/books/{id}/build + GET /api/books/{id}）
- 配置分层：application.yml + application-dev.yml，替换单文件 application.properties
- 禁用 Redis 自动连接（当前阶段不需要）

## 本阶段不做

- 不实现 AgentRun/AgentStep 追踪（等 Demo 2）
- 不实现前端页面
- 不接 Python 切章

## mock/临时实现

- 切章规则：正则 `第[一二三四五六七八九十百千\d]+回`（Debt → Demo 5 接 Python splitter）
- 作者硬编码为 "吴承恩"（Debt → 后续支持元数据填写）
- project_id 固定为 1（Debt → Demo 4 前补 User/Project）
- 文件编码硬编码为 GB18030（Debt → 后续支持编码检测）

## 学习目标

- 理解 Spring Boot 三层结构（Controller → Service → Repository）
- 理解 JPA 实体映射与 ddl-auto=update 建表
- 理解中文数字解析算法（一 → 1, 十 → 10, 一百 → 100）
- 理解配置分层（application.yml + application-dev.yml）

## 验收证据

- Maven test 通过（contextLoads）
- Apifox POST /api/books → Book(id=1, status=IMPORTED) 创建成功
- Apifox POST /api/books/1/build → 100 chapters 入库，status=READY_FOR_QA
- MySQL 查询确认：1 条 novel_book + 100 条 novel_chapter

## 已硬化

- application.properties → application.yml + application-dev.yml
- Redis 自动连接已禁用

## 风险

- 当前仅支持 GB18030 编码的 txt；其他编码和 md 格式需后续支持
- 简单正则对非回目体书籍（山海经、聊斋）无效

---

## 下一阶段：demo-2-agent-run

阶段 id：demo-2-agent-run
状态：planned
循环：demo-first
轮次：demo 2

### 功能目标

让构建任务可追踪：导入/切章/保存的每个步骤都记录在 AgentRun/AgentStep 中。

### 要做

- 创建 NovelAgentRun + NovelAgentStep 实体
- 实现 AgentRunService（创建 run、记录 step、状态流转）
- 改造 BookService.buildBook()：内部用 AgentRun/AgentStep 包裹
- 构建失败时 AgentRun 记录 errorMessage
- API：GET /api/agent-runs 查询构建任务状态

### 不做

- 不接 Python RAG
- 不接 LLM
