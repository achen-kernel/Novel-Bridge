# NovelBridge-Agents v1 详细开发计划

## 0. v1 目标

v1 只完成一条最小闭环：

```text
上传 txt/md 小说
-> 清洗文本
-> 切章节
-> 切 chunk
-> 建立 Chroma 和 SQLite FTS 索引
-> 抽取 ChapterFact
-> 保存 MySQL
-> 基于一本书问答
-> 返回答案和引用
-> SSE 展示过程
```

v1 不做复杂知识图谱、复杂 Book Wiki、多书问答、云同步、完整设定卡系统、复杂审核平台。

## 1. 阶段 0：项目基线

### 目标

建立三个服务和基础运行环境。

### 任务

```text
T0.1 梳理主目录结构，确认是否保留现有 D:\Novel-Bridge\Novel-Bridge 作为 backend/novelbridge-server
T0.2 建立项目级 README，说明三个服务启动方式
T0.3 后端补齐 actuator health、基础配置和统一返回结构
T0.4 创建 frontend/novelbridge-web，使用 Vue 3 + Vite + TypeScript + Pinia + Element Plus
T0.5 创建 rag-service，使用 FastAPI + Pydantic + pytest
T0.6 创建 docker/docker-compose.yml，包含 MySQL 8.x 和 Chroma
T0.7 创建 data/books、data/workspace、data/chroma、data/samples
T0.8 创建 docs/prompts，放置 v1 prompt 文件
```

### 验收

```text
后端 /actuator/health 可访问
前端 localhost:5173 可访问
Python /health 可访问
MySQL 可连接
Chroma heartbeat 可访问
README 能指导新 agent 启动项目
```

### 对抗检查

```text
是否引入了任务书之外的技术栈？
是否把后端骨架直接删除？
是否把 docs 写散到服务内部而不是项目级管理？
```

## 2. 阶段 1：基础业务模型

### 目标

建立可追踪的数据地基。

### 后端模块

```text
common
user
project
book
chapter
chunk
fact
agent
model
chat
citation
review
eval
```

### 必须实现的数据对象

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

### 预留对象

```text
EntityProfile
ReviewItem
PromptVersion
RetrieverVersion
EvalCase
EvalResult
```

预留对象可以先建轻量实体或文档说明，不做复杂业务。

### 数据库设计决策

```text
1. 使用单一数据库（novel_bridge），所有表通过 book_id 或 project_id 归属
   不采用"一书一库"方案，避免连接管理复杂化和阻碍后续多书问答
2. EntityProfile 在 v1 只建轻量实体表（id, book_id, entity_name, entity_type, aliases, status），不做跨章聚合逻辑
3. v1 中人物信息通过 ChapterFact(fact_type='CHARACTER') 按章存储
4. MySQL = localhost:3306/novel_bridge?useSSL=false&allowPublicKeyRetrieval=true&characterEncoding=utf-8mb4
5. Redis = localhost:6379（v1 先配置，暂不强制使用）
```

### 统一字段要求

```text
id
createdAt
updatedAt
createdBy
updatedBy
status
errorMessage
```

不要求每张表都有全部字段，但模型产物、长任务、审核对象必须有 `status`，失败对象必须能保存 `errorMessage`。

### 验收

```text
核心表可通过 migration 或 JPA ddl 创建
项目、文件夹、书籍、会话基础 CRUD 可用
AgentRun / AgentStep 能表达长任务
ModelRun 能记录模型调用元数据
Citation 能关联回答消息和证据来源
```

### 对抗检查

```text
是否所有模型产物都有 status？
是否所有长任务都有 AgentRun / AgentStep？
是否把 EntityProfile 做成了复杂 v2 功能？
```

## 3. 阶段 2：书籍导入

### 目标

用户上传 txt/md 文件，后端保存原文并创建 Book。

### 接口

```text
POST /api/books/import
GET  /api/books
GET  /api/books/{bookId}
GET  /api/books/{bookId}/chapters
GET  /api/books/{bookId}/chapters/{chapterId}
```

### 行为

```text
限制文件类型为 txt/md
限制文件大小
防止路径穿越
保存到 data/books 或配置目录
Book.status = IMPORTED
返回给前端的 sourcePath 不能暴露真实系统绝对路径
绑定 Project / Folder / User
```

### 验收

```text
合法 txt/md 可上传
非法扩展名被拒绝
超大文件被拒绝
路径穿越文件名被安全处理
Book 记录可查询
```

### 对抗检查

```text
是否把原始文件路径直接返回给用户？
是否绕过 Project / Folder / User 绑定？
```

## 4. 阶段 3：Python 文本清洗与章节切分

### 目标

Python RAG Service 完成文本读取、清洗、章节切分。

### 模块

```text
app/importer/text_loader.py
app/importer/text_cleaner.py
app/splitter/chapter_splitter.py
app/api/build.py
app/schemas/chapter_schema.py
tests/
```

### 接口

```text
GET  /health
POST /build/split-chapters
```

### 行为

```text
支持 UTF-8 txt/md
清理多余空行、不可见控制字符、常见广告分隔
支持“第1章 / 第一章 / 第001章”
支持中文章回体标题，如“第一回 灵根育孕源流出”
返回 chapterNo、title、content、startOffset、endOffset
章节编号连续
无法识别章节时返回可读错误，不静默生成错误章节
```

### 验收

```text
sample_01_short.txt 可正确切分
sample_02_medium.txt 可正确切分
章节标题不为空
章节内容不为空
pytest 覆盖普通章节和章回体
```

### 对抗检查

```text
是否用脆弱字符串规则导致所有小说都切成一章？
是否没有返回 offset，导致后续 evidence 无法追溯？
```

## 5. 阶段 4：BookBuildHarness MVP

### 目标

后端编排 Python 切章并保存 Chapter，同时通过 SSE 展示构建过程。

### 接口

```text
POST /api/books/{bookId}/build
GET  /api/books/{bookId}/build/events
GET  /api/agent-runs/{runId}
GET  /api/agent-runs/{runId}/steps
```

### 行为

```text
创建 AgentRun，type = BOOK_BUILD
创建 AgentStep，至少包含 CLEAN_TEXT、SPLIT_CHAPTERS、SAVE_TO_MYSQL
调用 Python /build/split-chapters
保存 Chapter
Book.status 从 IMPORTED -> BUILDING -> READY_FOR_QA 或 BUILD_FAILED
每个 SSE 事件使用统一 JSON，不返回裸字符串
失败时 AgentRun 和 AgentStep 都记录 errorMessage
```

### 验收

```text
点击构建后 AgentRun 为 RUNNING
章节保存到 MySQL
SSE 能展示进度
失败后可查询错误
重复构建有明确策略：v1 默认拒绝 READY_FOR_QA 书籍重复构建，除非显式 rebuild
```

### 对抗检查

```text
是否没有 AgentRun 就直接调用 Python？
是否构建失败但 Book 仍被标记 READY_FOR_QA？
```

## 6. 阶段 5：chunk 构建与索引

### 目标

章节切分为 chunk，并建立 Chroma / SQLite FTS 索引。

### Python 模块

```text
app/splitter/chunk_splitter.py
app/indexer/chroma_indexer.py
app/indexer/sqlite_fts_indexer.py
app/api/build.py
```

### 接口

```text
POST /build/chunks
POST /build/index
```

### 行为

```text
chunk 带 bookId、chapterId、chapterNo、chunkNo、startOffset、endOffset
后端保存 Chunk 元数据
Chroma 保存向量和 metadata
SQLite FTS 保存全文索引
Chunk 记录 vectorId
索引失败时记录具体失败层：VECTOR_INDEX 或 FTS_INDEX
```

### 验收

```text
每章能生成至少一个 chunk
chunk 保存到 MySQL
Chroma 可按 bookId 检索
SQLite FTS 可按关键词检索
metadata 包含 bookId / chapterId / chapterNo / chunkNo
```

### 对抗检查

```text
Java 是否直接操作了 Chroma？
chunk 是否丢失 offset，导致引用无法定位？
```

## 7. 阶段 6：ChapterFact 抽取

### 目标

每章生成结构化事实草稿。

### 文件

```text
docs/prompts/chapter_summary_v1.md
docs/prompts/chapter_fact_extract_v1.md
rag-service/app/extractor/chapter_fact_extractor.py
rag-service/app/extractor/json_repair.py
rag-service/app/extractor/evidence_validator.py
```

### ChapterFact v1 结构

```text
chapterNo
chapterTitle
summary
characters[]
locations[]
items[]
events[]
relationships[]
evidenceSpans[]
status = AUTO_EXTRACTED
```

### 行为

```text
prompt 从文件读取
模型输出先保存 rawOutputRef
JSON repair 只能修复格式，不能编造内容
evidence_validator 检查 evidenceText 是否出现在章节文本中
后端保存 ChapterFact
后端保存 ModelRun
低置信内容标记 NEED_FIX 或保留 AUTO_EXTRACTED
```

### 验收

```text
每章至少有 summary
JSON 可解析
ChapterFact 保存到 MySQL
ModelRun 保存 modelName / promptVersion / success / errorMessage
重要事件尽量有 evidenceText
```

### 对抗检查

```text
是否把 prompt 写进代码？
是否把模型输出直接标记 APPROVED？
是否没有保存 raw output，导致无法复盘？
```

## 8. 阶段 7：基础混合检索

### 目标

用户提问时能检索 ChapterFact 和 chunk。

### Python 模块

```text
app/retriever/hybrid_retriever.py
app/retriever/context_builder.py
app/api/query.py
```

### 接口

```text
POST /query
```

### 行为

```text
输入 bookId + question
检索 ChapterFact
检索 Chroma chunk
检索 SQLite FTS chunk
做简单融合排序
返回 sourceType、chapterId、chunkId、factId、evidenceText、score
```

### 验收

```text
问题能返回相关章节
能返回相关 chunk
能返回 evidenceText
能区分 CHAPTER_FACT / CHUNK
结果可被后端构造上下文
```

### 对抗检查

```text
是否只有向量检索，没有全文检索？
是否返回了无法追溯的纯文本片段？
```

## 9. 阶段 8：QueryAnswerHarness MVP

### 目标

用户可以基于一本书提问，系统保存消息、回答、引用和问题索引。

### 接口

```text
POST /api/books/{bookId}/chat-sessions
GET  /api/books/{bookId}/chat-sessions
GET  /api/chat-sessions/{sessionId}/messages
POST /api/chat-sessions/{sessionId}/ask
GET  /api/chat-sessions/{sessionId}/events
GET  /api/chat-sessions/{sessionId}/question-index
GET  /api/messages/{messageId}/citations
```

### 行为

```text
保存用户 ChatMessage
创建 AgentRun，type = QUERY_ANSWER
调用 Python /query
构造上下文
调用本地 9B 模型
保存 Assistant ChatMessage
保存 Citation
生成 ChatQuestionIndex
通过 SSE 推送 QUERY_RECEIVED 到 ANSWER_FINISHED
```

### 验收

```text
能创建会话
能提问
能得到回答
回答有引用卡片数据
刷新后历史消息仍存在
右侧问题索引可查询
```

### 对抗检查

```text
是否没有检索直接问模型？
是否回答保存了但 Citation 没保存？
是否模型回答中出现无证据断言？
```

## 10. 阶段 9：前端 AI 阅读工作台

### 目标

构建三栏式 AI 阅读工作台。

### 页面

```text
登录页
工作区首页
项目/书架页
书籍导入页
构建进度页
章节阅读页
问答工作台页
```

### 布局

```text
左侧：项目 / 文件夹 / 书籍 / 历史对话
中间：当前书籍、问答消息、引用卡片、输入框、过程事件
右侧：当前对话问题索引、引用来源、相关章节、知识资产操作入口
```

### 验收

```text
可选择书籍和历史对话
可上传书籍
可查看构建进度 SSE
可提问
可查看回答引用
点击问题索引可滚动到对应消息
前端不是单一聊天窗口
```

### 对抗检查

```text
是否做成了普通聊天页？
是否没有展示 Citation？
是否没有展示构建和问答过程？
```

## 11. 阶段 10：质量验证

### 目标

v1 不是“看起来能跑”，而是可验证。

### 任务

```text
准备 data/samples/sample_01_short.txt
准备 data/samples/sample_02_medium.txt
准备 data/samples/golden_questions.json
编写章节切分测试
编写 ChapterFact JSON 测试
编写问答引用测试
编写 README 完整流程
```

### 验收

```text
样例书可完整构建
章节切分结果可人工检查
ChapterFact 可解析
黄金问题能命中相关章节
引用能追溯 chapter/chunk/fact
README 可让新开发者跑通
```

### v1 最终红线

```text
没有 AgentRun / AgentStep，不算完成
没有 Citation，不算完成问答
没有样例验证，不算完成构建
没有 promptVersion，不算完成模型调用
没有 errorMessage，不算完成失败处理
```

