# NovelBridge-Agents Vibecoding 开发任务书 v1

## 0. 文档定位

本任务书用于指导 NovelBridge-Agents 从 0 到 1 开发。

本项目不是普通的“小说切片 + 向量检索 + 聊天”系统，而是面向小说、资料、设定集的 **单书知识资产构建与可追溯问答系统**。项目核心是为每本书构建可审核、可追溯、可检索、可持续扩展的 Book Memory Package，本地 9B 模型不负责记住整本书，而是基于构建好的知识资产进行回答。

本任务书的第一目标是：

```text
先打好可扩展地基，再逐步增加智能能力。
```

------

# 1. 第一版总目标

## 1.1 MVP 目标

第一版只完成一条最小闭环：

```text
上传一本 txt/md 小说
-> 自动清洗文本
-> 自动切章节
-> 自动切 chunk
-> 生成 ChapterFact
-> 保存 MySQL
-> 建立简单检索
-> 用户针对该书提问
-> 本地 9B 模型回答
-> 返回章节和原文引用
-> SSE 展示构建 / 回答过程
```

这与项目蓝图中定义的第一版 MVP 范围一致：上传 txt/md 小说、自动切章节、切 chunk、生成 ChapterFact、保存 MySQL、建立简单检索、问答、返回引用、SSE 展示进度。

## 1.2 第一版不做

第一版明确不做：

```text
完整知识图谱
复杂 Book Wiki
自动百科爬取
云端同步
多书联合问答
每本书训练模型
复杂多智能体
完整设定集系统
复杂审核平台
复杂 EvalHarness 平台
```

但第一版必须预留扩展能力：

```text
Project / Folder / ChatSession
AgentRun / AgentStep
ModelRun
Citation
PromptVersion
RetrieverVersion
Review 状态字段
Eval 数据结构预留
EntityProfile 预留
```

------

# 2. 项目最高设计原则

所有代码和功能都要服从以下原则：

```text
每个模型产物都有来源
每个任务步骤都可追踪
每个回答都可引用
每个重要知识都可人工审核
每次改动都可评测
每本书都能沉淀为长期可用的知识资产
```

这是项目蓝图中明确提出的最终设计原则，也是本项目区别于普通 RAG 聊天项目的核心。

------

# 3. 总体架构

## 3.1 服务架构

```text
Vue 前端
  -> Spring Boot 后端
      -> MySQL 权威知识库
      -> LangChain4j 调用本地 9B 模型
      -> RemoteRagClient 调用 Python RAG 服务
          -> Chroma 向量库
          -> SQLite FTS 全文检索
          -> 文本清洗 / 切章 / chunk / 抽取 / 检索
```

## 3.2 职责边界

| 模块             | 职责                                                         |
| ---------------- | ------------------------------------------------------------ |
| Vue 前端         | AI 阅读工作台、项目/书籍/对话管理、构建进度、问答交互、引用展示 |
| Spring Boot 后端 | 业务系统、权限、项目/书籍/章节/任务、SSE、聊天记录、引用记录、模型调用编排 |
| Python RAG 服务  | 文本清洗、章节切分、chunk、embedding、Chroma、SQLite FTS、ChapterFact 抽取、检索 |
| MySQL            | 权威知识资产、业务数据、任务数据、引用数据                   |
| Chroma           | 向量检索辅助层                                               |
| SQLite FTS       | 全文检索辅助层                                               |
| 本地 9B 模型     | 摘要、抽取、问答、草稿生成                                   |

蓝图中也明确推荐了“Vue -> Spring Boot -> MySQL / Python RAG / Chroma / SQLite FTS / 本地 9B”的职责划分。

------

# 4. 技术选型固定

## 4.1 后端

```text
Java 21
Spring Boot 3.x
Spring MVC
Spring Security
Spring Data JPA
MySQL Driver
Validation
Lombok
LangChain4j
Springdoc OpenAPI
```

第一版建议使用 Spring MVC，不强行上 WebFlux。SSE 可以使用 `SseEmitter` 实现。

## 4.2 前端

```text
Vue 3
Vite
TypeScript
Pinia
Vue Router
Element Plus
fetch / EventSource
```

前端不是普通聊天页，而是三栏式 AI 阅读工作台。

## 4.3 Python RAG 服务

```text
Python 3.12
FastAPI
Uvicorn
Pydantic
Chroma
SQLite FTS5
sentence-transformers
OpenAI-compatible client
pytest
```

## 4.4 数据库与中间件

```text
MySQL 8.x
Chroma
SQLite FTS5
Redis 第二阶段再接入
```

## 4.5 模型

```text
本地 9B 左右模型
OpenAI-compatible API
默认地址：http://localhost:11434/v1
```

模型只负责理解、抽取、表达，不负责长期记忆。

------

# 5. 项目目录结构

建议从一开始采用以下结构：

```text
novelbridge-agents/
  backend/
    novelbridge-server/
  frontend/
    novelbridge-web/
  rag-service/
    app/
      api/
      core/
      importer/
      splitter/
      indexer/
      extractor/
      retriever/
      evaluator/
      schemas/
      utils/
    tests/
    requirements.txt
    .env.example
  docs/
    dev-env.md
    api.md
    architecture.md
    prompts/
      chapter_fact_extract_v1.md
      qa_with_citation_v1.md
  data/
    books/
    workspace/
    chroma/
    samples/
  scripts/
    start-dev.sh
    stop-dev.sh
    init-db.sql
  docker/
    docker-compose.yml
  README.md
  .gitignore
```

项目蓝图中已经建议从头构建 `backend / frontend / rag-service / docs / data / scripts` 这种结构，本任务书在此基础上补充了 prompts、schemas、tests、docker 等长期扩展目录。

------

# 6. 第一版核心数据模型

## 6.1 第一版必须实现

```text
User
Project
Folder
Book
Chapter
Chunk
ChapterFact
AgentRun
AgentStep
ModelRun
ChatSession
ChatMessage
ChatQuestionIndex
Citation
```

其中，`Project / Folder / ChatSession / ChatQuestionIndex` 是为了支持未来网页端的人性化问答工作台，包括不同项目、文件夹、历史对话、当前对话索引。

## 6.2 第一版预留但不完整实现

```text
EntityProfile
EntityAlias
EntityMention
ReviewItem
PromptVersion
RetrieverVersion
EvalCase
EvalResult
```

第一版可以建表，也可以先只保留实体类和接口占位，但不要做复杂业务。

## 6.3 后期再实现

```text
EntityNode
EntityEdge
BookWikiPage
BookWikiCitation
SettingCard
SettingCollection
SyncJob
ExternalSource
```

------

# 7. 关键状态枚举

所有模型生成内容、构建任务、审核对象都必须有状态。

## 7.1 通用内容状态

```text
DRAFT
AUTO_EXTRACTED
REVIEWING
APPROVED
REJECTED
NEED_FIX
```

## 7.2 任务状态

```text
PENDING
RUNNING
SUCCESS
FAILED
CANCELED
PARTIAL_SUCCESS
```

## 7.3 书籍状态

```text
IMPORTED
BUILDING
READY_FOR_QA
BUILD_FAILED
NEED_REVIEW
ARCHIVED
```

## 7.4 AgentStep 状态

```text
WAITING
RUNNING
SUCCESS
FAILED
RETRYING
SKIPPED
```

------

# 8. 前端产品形态：AI 阅读工作台

第一版前端不能只做成普通聊天窗口，而要做成三栏式工作台。

## 8.1 页面结构

```text
左侧：项目 / 文件夹 / 书籍 / 历史对话
中间：当前问答主区域
右侧：当前对话索引 / 引用来源 / 相关实体 / 知识资产操作
```

## 8.2 第一版页面

```text
登录页
工作区首页
项目/书架页
书籍导入页
构建进度页
章节阅读页
问答工作台页
```

## 8.3 问答工作台要求

中间区域：

```text
当前书籍信息
当前问答模式
聊天消息
AI 回答
引用卡片
输入框
SSE 流式过程
```

右侧区域：

```text
当前对话问题索引
引用来源列表
相关章节
相关人物/地点/事件
收藏 / 保存 / 导出入口
```

## 8.4 当前对话索引

用户每问一个问题，系统要生成一个索引项：

```text
questionText
messageId
answerMessageId
sortOrder
tagsJson
createdAt
```

前端表现类似：

```text
当前对话
────────────────
三打白骨精的原因
唐僧为什么误会孙悟空
白骨精三次变化
这一回的人物冲突
```

点击索引项后，滚动到对应问答位置。当前问题高亮显示。

------

# 9. 后端核心模块

## 9.1 包结构建议

```text
com.novelbridge.server
  common/
    config/
    exception/
    response/
    security/
    util/
  user/
  project/
  book/
  chapter/
  chunk/
  fact/
  agent/
  model/
  chat/
  citation/
  rag/
  llm/
  sse/
  review/
  eval/
```

## 9.2 后端模块职责

| 模块     | 职责                                          |
| -------- | --------------------------------------------- |
| user     | 用户、登录、权限                              |
| project  | 项目、文件夹                                  |
| book     | 书籍导入、书籍状态                            |
| chapter  | 章节管理                                      |
| chunk    | chunk 元数据管理                              |
| fact     | ChapterFact 保存、查询                        |
| agent    | AgentRun / AgentStep                          |
| model    | ModelRun、模型调用记录                        |
| chat     | ChatSession / ChatMessage / ChatQuestionIndex |
| citation | 回答引用来源                                  |
| rag      | 调用 Python RAG 服务                          |
| llm      | 调用本地模型                                  |
| sse      | 构建进度和问答过程推送                        |
| review   | 审核预留                                      |
| eval     | 评测预留                                      |

------

# 10. Python RAG 服务模块

## 10.1 目录结构

```text
rag-service/
  app/
    api/
      health.py
      build.py
      query.py
      extract.py
    importer/
      text_loader.py
      text_cleaner.py
    splitter/
      chapter_splitter.py
      chunk_splitter.py
    indexer/
      chroma_indexer.py
      sqlite_fts_indexer.py
    extractor/
      chapter_fact_extractor.py
      json_repair.py
      evidence_validator.py
    retriever/
      hybrid_retriever.py
      context_builder.py
    evaluator/
      golden_eval.py
    schemas/
      book_schema.py
      chapter_schema.py
      fact_schema.py
      query_schema.py
    core/
      config.py
      llm_client.py
      logging.py
```

## 10.2 Python 服务接口

第一版必须实现：

```text
GET  /health
POST /build/split-chapters
POST /build/chunks
POST /build/index
POST /extract/chapter-fact
POST /query
```

后期再扩展：

```text
POST /build/book
GET  /tasks/{taskId}
POST /eval/run
POST /entity/profile
POST /graph/build
```

------

# 11. SSE 事件协议

为了后续可追踪，SSE 不要随便返回字符串，必须使用统一事件格式。

## 11.1 构建进度事件

```json
{
  "runId": 1,
  "stepName": "splitChapters",
  "status": "RUNNING",
  "message": "正在识别章节结构",
  "progress": 35,
  "timestamp": "2026-xx-xxTxx:xx:xx"
}
```

## 11.2 问答过程事件

```json
{
  "runId": 2,
  "eventType": "RETRIEVAL",
  "status": "SUCCESS",
  "message": "已命中 3 个章节事实和 5 个原文片段",
  "data": {
    "chapterHits": [12, 13, 14],
    "chunkCount": 5
  }
}
```

## 11.3 必须支持的事件类型

```text
BOOK_IMPORTED
CLEAN_TEXT
SPLIT_CHAPTERS
BUILD_CHUNKS
BUILD_VECTOR_INDEX
BUILD_FTS_INDEX
EXTRACT_CHAPTER_FACT
SAVE_TO_MYSQL
READY_FOR_QA

QUERY_RECEIVED
INTENT_DETECTED
RETRIEVAL_STARTED
RETRIEVAL_FINISHED
CONTEXT_BUILT
LLM_ANSWERING
CITATION_VALIDATED
ANSWER_FINISHED
ERROR
```

------

# 12. Prompt 版本管理

第一版至少准备 3 个 prompt 文件：

```text
docs/prompts/
  chapter_summary_v1.md
  chapter_fact_extract_v1.md
  qa_with_citation_v1.md
```

每次模型调用必须记录：

```text
modelName
promptVersion
temperature
inputTokenEstimate
outputTokenEstimate
rawInputRef
rawOutputRef
success
errorMessage
createdAt
```

不要让 prompt 散落在代码里。

------

# 13. ChapterFact 第一版结构

第一版 ChapterFact 不要设计过重，建议采用可扩展 JSON：

```json
{
  "chapterNo": 1,
  "chapterTitle": "",
  "summary": "",
  "characters": [
    {
      "name": "",
      "aliases": [],
      "roleInChapter": "",
      "evidenceText": ""
    }
  ],
  "locations": [
    {
      "name": "",
      "evidenceText": ""
    }
  ],
  "items": [
    {
      "name": "",
      "owner": "",
      "evidenceText": ""
    }
  ],
  "events": [
    {
      "event": "",
      "participants": [],
      "location": "",
      "evidenceText": ""
    }
  ],
  "relationships": [
    {
      "source": "",
      "target": "",
      "relation": "",
      "evidenceText": ""
    }
  ],
  "evidenceSpans": [
    {
      "text": "",
      "startOffset": 0,
      "endOffset": 0
    }
  ]
}
```

第一版必须做到：

```text
JSON 可解析
章节编号正确
至少有 summary
重要事件尽量有 evidenceText
低置信内容 status = AUTO_EXTRACTED
```

------

# 14. API 设计

## 14.1 项目与文件夹

```text
POST   /api/projects
GET    /api/projects
GET    /api/projects/{projectId}
PUT    /api/projects/{projectId}
DELETE /api/projects/{projectId}

POST   /api/folders
GET    /api/projects/{projectId}/folders
PUT    /api/folders/{folderId}
DELETE /api/folders/{folderId}
```

## 14.2 书籍

```text
POST /api/books/import
GET  /api/books
GET  /api/books/{bookId}
GET  /api/books/{bookId}/chapters
GET  /api/books/{bookId}/chapters/{chapterId}
```

## 14.3 构建任务

```text
POST /api/books/{bookId}/build
GET  /api/books/{bookId}/build/events
GET  /api/agent-runs/{runId}
GET  /api/agent-runs/{runId}/steps
```

## 14.4 ChapterFact

```text
GET /api/books/{bookId}/facts
GET /api/chapters/{chapterId}/fact
```

## 14.5 问答

```text
POST /api/books/{bookId}/chat-sessions
GET  /api/books/{bookId}/chat-sessions
GET  /api/chat-sessions/{sessionId}/messages
POST /api/chat-sessions/{sessionId}/ask
GET  /api/chat-sessions/{sessionId}/events
GET  /api/chat-sessions/{sessionId}/question-index
```

## 14.6 引用

```text
GET /api/messages/{messageId}/citations
GET /api/citations/{citationId}
```

------

# 15. Vibecoding 开发阶段

## 阶段 0：项目基线

目标：

```text
创建干净的新项目，三个服务能启动。
```

任务：

```text
T0.1 创建 Git 仓库和目录结构
T0.2 创建 Spring Boot 项目
T0.3 创建 Vue 3 项目
T0.4 创建 FastAPI 项目
T0.5 配置 docker-compose：MySQL + Chroma
T0.6 编写 README.md
T0.7 编写 docs/dev-env.md
```

验收标准：

```text
后端 localhost:8080/actuator/health 可访问
前端 localhost:5173 可访问
Python localhost:5222/health 可访问
MySQL 可连接
Chroma 可 heartbeat
README 可指导启动项目
```

------

## 阶段 1：基础业务模型

目标：

```text
建立可扩展的数据地基。
```

任务：

```text
T1.1 实现 User 基础模型
T1.2 实现 Project 模型
T1.3 实现 Folder 模型
T1.4 实现 Book 模型
T1.5 实现 Chapter 模型
T1.6 实现 Chunk 模型
T1.7 实现 AgentRun / AgentStep
T1.8 实现 ChatSession / ChatMessage / ChatQuestionIndex
T1.9 实现 Citation
```

验收标准：

```text
数据库表可自动创建或由 migration 创建
实体关系清晰
所有核心表有 createdAt / updatedAt
所有模型产物有 status
项目、文件夹、书籍、对话可以 CRUD
```

------

## 阶段 2：书籍导入

目标：

```text
用户可以上传 txt/md 文件，后端保存 Book，并将原文持久化。
```

任务：

```text
T2.1 实现 POST /api/books/import
T2.2 文件类型限制 txt/md
T2.3 文件大小限制
T2.4 防止路径穿越
T2.5 保存 sourcePath
T2.6 创建 Book 记录
T2.7 绑定 Project / Folder / User
```

验收标准：

```text
上传 txt/md 成功
非法文件被拒绝
Book 状态为 IMPORTED
文件保存路径不暴露真实系统路径
```

------

## 阶段 3：Python 文本清洗与章节切分

目标：

```text
Python 服务完成文本清洗和章节切分。
```

任务：

```text
T3.1 实现 text_loader
T3.2 实现 text_cleaner
T3.3 实现 chapter_splitter
T3.4 支持中文章回体标题
T3.5 支持普通“第x章”标题
T3.6 返回章节列表 JSON
T3.7 编写 pytest 测试
```

验收标准：

```text
sample_01_short.txt 可正确切分
sample_02_medium.txt 可正确切分
章节编号连续
章节标题不为空
章节内容不为空
```

------

## 阶段 4：BookBuildHarness MVP

目标：

```text
后端编排 Python 服务，完成构建任务追踪。
```

任务：

```text
T4.1 实现 POST /api/books/{bookId}/build
T4.2 创建 AgentRun
T4.3 创建 AgentStep
T4.4 调用 Python split-chapters
T4.5 保存 Chapter
T4.6 失败时记录 errorMessage
T4.7 实现 GET /api/books/{bookId}/build/events
```

验收标准：

```text
点击构建后 AgentRun 状态变为 RUNNING
每个步骤有 AgentStep 记录
章节保存到 MySQL
SSE 能显示构建进度
失败后可查看错误原因
```

------

## 阶段 5：chunk 构建与索引

目标：

```text
章节被切成 chunk，并建立 Chroma / SQLite FTS 检索索引。
```

任务：

```text
T5.1 Python 实现 chunk_splitter
T5.2 后端保存 Chunk 元数据
T5.3 Python 实现 chroma_indexer
T5.4 Python 实现 sqlite_fts_indexer
T5.5 Chunk 记录 vectorId
T5.6 建立 bookId / chapterId / chunkNo 元数据
```

验收标准：

```text
每章可生成 chunk
chunk 可保存到 MySQL
Chroma 可按 bookId 检索
SQLite FTS 可按关键词检索
chunk metadata 包含 bookId、chapterId、chapterNo、chunkNo
```

------

## 阶段 6：ChapterFact 抽取

目标：

```text
每章生成结构化 ChapterFact。
```

任务：

```text
T6.1 编写 chapter_fact_extract_v1.md
T6.2 Python 实现 chapter_fact_extractor
T6.3 Python 实现 json_repair
T6.4 Python 实现 evidence_validator 简化版
T6.5 后端保存 ChapterFact
T6.6 记录 ModelRun
T6.7 ChapterFact status 默认为 AUTO_EXTRACTED
```

验收标准：

```text
每章至少生成 summary
JSON 解析成功率达到基本可用
ChapterFact 保存到 MySQL
ModelRun 保存模型名和 promptVersion
有 evidenceText 字段
```

------

## 阶段 7：基础混合检索

目标：

```text
用户提问时，系统可以检索 ChapterFact 和 chunk。
```

任务：

```text
T7.1 Python 实现 hybrid_retriever
T7.2 支持 ChapterFact 检索
T7.3 支持 Chroma 向量检索
T7.4 支持 SQLite FTS 检索
T7.5 实现简单融合排序
T7.6 返回命中章节、chunk、证据片段
```

验收标准：

```text
输入问题后能返回相关章节
能返回相关 chunk
能返回 sourceType
能返回 evidenceText
检索结果可以被后端用于构造上下文
```

------

## 阶段 8：基础问答 QueryAnswerHarness

目标：

```text
用户可以在问答工作台中基于一本书提问。
```

任务：

```text
T8.1 实现 ChatSession
T8.2 实现 POST /api/chat-sessions/{sessionId}/ask
T8.3 后端创建 Query AgentRun
T8.4 调用 Python /query
T8.5 构造上下文
T8.6 调用本地 9B 模型
T8.7 保存用户消息和 AI 消息
T8.8 保存 Citation
T8.9 生成 ChatQuestionIndex
```

验收标准：

```text
用户可以创建会话
用户可以提问
AI 可以回答
回答包含引用来源
消息可持久化
刷新页面后历史对话仍存在
右侧问题索引可展示
```

------

## 阶段 9：前端 AI 阅读工作台

目标：

```text
实现人性化问答界面。
```

任务：

```text
T9.1 实现三栏式布局
T9.2 左侧项目 / 文件夹 / 书籍 / 历史对话
T9.3 中间聊天区
T9.4 右侧当前对话索引
T9.5 右侧引用来源列表
T9.6 AI 回答引用卡片
T9.7 构建进度 SSE 展示
T9.8 问答过程 SSE 展示
```

验收标准：

```text
用户能从左侧选择书籍和历史对话
中间能正常问答
右侧能看到问题列表
点击问题索引能跳转到对应消息
回答下方显示引用卡片
构建进度实时显示
```

------

## 阶段 10：基础质量与测试

目标：

```text
保证第一版不是“看起来能跑”，而是真的可验证。
```

任务：

```text
T10.1 准备 sample_01_short.txt
T10.2 准备 sample_02_medium.txt
T10.3 准备 golden_questions.json
T10.4 编写章节切分测试
T10.5 编写 ChapterFact JSON 测试
T10.6 编写问答引用测试
T10.7 编写 README 使用流程
```

验收标准：

```text
样例书籍可完整构建
章节切分结果可人工检查
ChapterFact 可解析
问答能命中相关章节
引用能追溯到 chapter/chunk
README 能指导完整运行
```

------

# 16. Coding Agent 开发规则

每次让 coding agent 写代码时，都必须附带以下约束：

```text
当前只实现本阶段任务，不提前实现后期功能。
不能随意更换技术栈。
不能把 prompt 写死在业务代码里。
不能让 Python 服务承担用户权限和业务管理。
不能让 Java 后端直接操作 Chroma。
不能跳过 AgentRun / AgentStep。
不能生成没有来源的权威知识。
不能把模型输出直接标记为 APPROVED。
所有接口要有统一返回结构。
所有错误要有可读 errorMessage。
```

------

# 17. 每个任务的标准提示词模板

后续投喂给 coding agent 时，可以使用这个模板：

```text
你现在负责 NovelBridge-Agents 项目的【任务编号：Txx】。

项目定位：
NovelBridge-Agents 是单书知识资产构建与可追溯问答系统，不是普通聊天 RAG。

当前任务目标：
【填写本任务目标】

必须遵守：
1. 只实现当前任务，不提前实现后期功能。
2. 保持现有目录结构。
3. 后端负责业务编排，Python 负责文本处理和检索。
4. 所有模型生成内容必须有 status。
5. 所有长任务必须记录 AgentRun / AgentStep。
6. 所有回答必须可保存 Citation。
7. 不要引入未确认的新技术栈。

需要修改的目录：
【填写目录】

需要实现的接口：
【填写接口】

验收标准：
【填写验收标准】

请先说明你将修改哪些文件，再给出代码。
```

------

# 18. 第一版完成标志

当以下事情全部完成，才算 v1 地基完成：

```text
1. 三个服务可以稳定启动
2. MySQL / Chroma 可以连接
3. 可以上传一本 txt/md 小说
4. 可以自动切章节
5. 可以自动切 chunk
6. 可以生成 ChapterFact
7. 可以保存 Book / Chapter / Chunk / ChapterFact
8. 可以记录 AgentRun / AgentStep / ModelRun
9. 可以建立向量和全文检索
10. 可以基于一本书提问
11. 可以返回答案和引用
12. 可以保存 ChatSession / ChatMessage / Citation
13. 前端有三栏式问答工作台
14. 当前对话有问题索引
15. 构建和问答过程可以通过 SSE 展示
16. README 能让新开发者跑通项目
```

------

# 19. 后续扩展路线

v1 地基完成后，再按这个顺序扩展：

```text
v1.1 EntityProfile：人物、地点、物品、事件聚合
v1.2 ReviewHarness：审核队列、人工确认、APPROVED 优先
v1.3 Book Wiki：章节索引、人物档案、事件线
v1.4 EvalHarness：黄金问答集、prompt 对比、检索策略对比
v1.5 轻量知识图谱：EntityNode / EntityEdge / 关系图
v1.6 设定卡系统：人物卡、地点卡、物品卡、世界观规则卡
v1.7 云端同步与外部资料增强
```

------

# 20. 当前最建议先做的 3 件事

```text
第一步：创建项目骨架和 docker-compose
第二步：实现后端基础数据模型
第三步：实现 Python 章节切分服务
```

不要一开始就写复杂问答，不要一开始就做知识图谱，也不要一开始就做 Book Wiki。
先让系统具备最小生命线：

```text
书能导入
章节能切开
任务能追踪
数据能保存
前端能看到
```

这就是 NovelBridge-Agents 的地基。