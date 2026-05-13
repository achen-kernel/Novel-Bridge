# NovelBridge-Agents 项目简介

## 1. 项目定位

**NovelBridge-Agents** 是一个面向小说、神话资料和个人设定集的 **单书知识资产构建与可追溯问答系统**。

它不是普通的“小说切片 + 向量检索 + 聊天”项目，而是希望把每一本书构建成一个长期可用的 **Book Memory Package**。系统会围绕一本书自动生成章节事实、实体资料、人物关系、事件线、引用证据，并支持后续问答、分析、审核和知识沉淀。

一句话概括：

```text
NovelBridge-Agents = 单书知识资产构建 + 可追溯问答 + 人工审核 + 持续评测
```

------

## 2. 为什么要做这个项目

普通 RAG 对小说类文本效果有限，因为小说不是简单知识片段集合，而是包含：

```text
人物别名与身份变化
跨章节剧情因果
动态人物关系
地点、组织、法宝、世界观规则
神话典故与原型
用户个人设定和阅读笔记
```

所以本项目不希望模型“临时读几段文本然后回答”，而是先把一本书加工成结构化、可引用、可审核的知识资产，再基于这些资产进行问答和分析。

本地 9B 左右模型主要负责阅读、抽取、总结和表达，不负责长期记住整本书；长期知识应保存在 MySQL、ChapterFact、Book Wiki、EntityProfile 和检索索引中。

------

## 3. 第一版 MVP 做什么

第一版只跑通最小闭环：

```text
用户上传一本 txt/md 小说
        ↓
系统自动清洗文本
        ↓
自动识别目录并切分章节
        ↓
将章节切分为 chunk
        ↓
构建 Chroma 向量索引和 SQLite FTS 全文索引
        ↓
每章抽取 ChapterFact
        ↓
保存 Book、Chapter、Chunk、ChapterFact 到 MySQL
        ↓
用户针对该书提问
        ↓
系统检索 ChapterFact 和原文 chunk
        ↓
本地 9B 模型生成回答
        ↓
返回答案、章节来源和原文引用
        ↓
前端通过 SSE 展示构建和问答过程
```

第一版不做复杂知识图谱、复杂 Book Wiki、云端同步、多书联合问答、每本书训练模型、复杂多智能体和完整设定集系统。

------

## 4. 核心设计思想

项目的核心不是“大模型聊天”，而是 **Harness Engineering**。

模型只负责：

```text
输入文本 -> 输出摘要 / 事实 / 回答
```

Harness 负责：

```text
流程编排
状态管理
工具调用
结果校验
失败重试
人工审核
引用追踪
评测对比
```

主要 Harness 包括：

```text
BookBuildHarness：构建单书知识资产
QueryAnswerHarness：完成基于证据的问答
ReviewHarness：人工审核 AI 生成内容
EvalHarness：评估 prompt、模型、检索策略是否变好
```

其中第一版重点实现：

```text
BookBuildHarness MVP
QueryAnswerHarness MVP
```

------

## 5. 系统架构

推荐架构如下：

```text
Vue 前端
  -> Spring Boot 后端
      -> MySQL 本地权威库
      -> LangChain4j 调用本地 9B 模型
      -> RemoteRagClient 调用 Python RAG 服务
          -> Chroma 向量检索
          -> SQLite FTS 全文检索
          -> 文本清洗 / 切章 / chunk / 抽取 / 检索
```

职责边界：

```text
Spring Boot：
业务系统、用户权限、书籍管理、任务状态、SSE、聊天记录、引用记录、审核与知识资产管理。

Python RAG Service：
文本清洗、目录识别、章节切分、chunk 构建、embedding、Chroma 入库、SQLite FTS、ChapterFact 抽取、混合检索、评测脚本。

MySQL：
保存权威知识资产和业务数据。

Chroma：
负责向量检索。

SQLite FTS：
负责关键词全文检索。

本地 9B 模型：
负责摘要、事实抽取、设定草稿、基于上下文回答。
```

蓝图中也明确了这一职责划分：Spring Boot 管业务系统和编排，Python 管文本处理与检索，MySQL 是权威知识资产，Chroma 和 SQLite FTS 是检索辅助层，本地模型负责回答与生成。

------

## 6. 技术栈

第一版建议技术栈：

```text
后端：
Java 21
Spring Boot 3.x
Spring MVC
Spring Security
Spring Data JPA
LangChain4j
MySQL

前端：
Vue 3
Vite
TypeScript
Pinia
Element Plus
EventSource / fetch

Python RAG 服务：
Python 3.12
FastAPI
Chroma
SQLite FTS5
sentence-transformers
OpenAI-compatible LLM Client

模型：
本地 9B 左右模型
OpenAI-compatible API
默认地址：http://localhost:11434/v1
```

------

## 7. 前端产品形态

前端不是普通聊天窗口，而是一个 **AI 阅读工作台**。

推荐三栏式布局：

```text
左侧：项目 / 文件夹 / 书籍 / 历史对话
中间：当前问答、AI 回答、引用卡片、输入框
右侧：当前对话问题索引、引用来源、相关实体、知识资产操作
```

核心体验：

```text
用户可以管理不同项目和书籍
用户可以查看历史对话
当前对话内有清晰的问题索引
AI 回答带章节和原文引用
引用可以跳转到章节或 chunk
有价值回答后续可以沉淀为设定卡、Wiki 草稿或审核项
```

------

## 8. 核心数据对象

第一版重点对象：

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

后续扩展对象：

```text
EntityProfile
EntityAlias
EntityMention
ReviewItem
BookWikiPage
EntityNode
EntityEdge
EvalCase
EvalResult
SettingCard
SyncJob
```

第一版重点不是把所有表做完，而是先保证核心链路可追踪：

```text
一本书从上传到构建，有 AgentRun / AgentStep
每章事实有 ChapterFact
每次模型调用有 ModelRun
每次回答有 ChatMessage
每个引用有 Citation
每个问题能进入 ChatQuestionIndex
```

------

## 9. 第一版开发顺序

建议按以下顺序开发：

```text
阶段 0：项目基线
创建 backend、frontend、rag-service 三个服务，连接 MySQL、Chroma、本地模型。

阶段 1：BookBuildHarness MVP
实现上传书籍、文本清洗、章节切分、chunk 构建、ChapterFact 抽取、保存 MySQL、SSE 展示进度。

阶段 2：基础问答
检索 ChapterFact 和 chunk，调用本地 9B 模型回答，返回引用来源。

阶段 3：前端 AI 阅读工作台
实现项目/书籍/历史对话、当前问答、右侧问题索引、引用卡片。

阶段 4：基础质量验证
准备样例小说和黄金问题，测试章节切分、ChapterFact JSON、引用命中情况。
```

项目蓝图中推荐的开发顺序也是先做项目基线、BookBuildHarness MVP、基础问答，再逐步扩展 EntityProfile、Book Wiki、ReviewHarness、EvalHarness、轻量知识图谱和设定卡系统。

------

## 10. 项目开发原则

开发时必须遵守：

```text
1. 不要把本项目做成普通聊天 RAG。
2. 第一版只实现 MVP，不提前做复杂图谱和 Wiki。
3. MySQL 是权威知识库，Chroma / SQLite FTS 只是检索辅助。
4. Spring Boot 负责业务编排，Python 负责知识处理。
5. 所有模型生成内容默认是草稿，不直接成为权威知识。
6. 所有重要内容必须能追溯来源。
7. 所有长任务必须有 AgentRun / AgentStep。
8. 所有回答必须尽量保存 Citation。
9. Prompt 要版本化，不要散落在代码里。
10. 每次功能改动后，要能通过样例书籍和黄金问题检查效果。
```

最终判断项目是否优秀，不看概念多不多，而看：

```text
每个模型产物是否有来源
每个任务步骤是否可追踪
每个回答是否可引用
每个重要知识是否可审核
每次改动是否可评测
每本书是否能沉淀为长期可用的知识资产
```

这也是项目蓝图中给出的最终设计原则。