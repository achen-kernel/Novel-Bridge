# NovelBridge-Agents 总Plan

## 0. 给 Agent 的执行原则

本项目是 **单书知识资产构建与可追溯问答系统**，不是普通“小说切片 + 向量检索 + 聊天”。任何 agent 接手任务时，先遵守以下优先级：

```text
可追溯 > 可审核 > 可评测 > 可扩展 > 功能炫技
```

每次开发只做当前阶段，不提前实现后期功能。所有长任务必须经过 `AgentRun / AgentStep`，所有模型调用必须记录 `ModelRun`，所有回答必须尽量保存 `Citation`，所有模型产物默认是草稿或自动抽取状态，不能直接标记为权威知识。

## 1. 当前已知状态

```text
主目录：D:\Novel-Bridge
现有后端骨架：D:\Novel-Bridge\Novel-Bridge
当前后端包名：com.achen.novelbridge
当前后端状态：Spring Boot 初始工程
当前缺口：frontend、rag-service、docker、docs、data、scripts 尚未形成完整项目级结构
```

后续 agent 不要直接删除现有后端工程。若需要调整目录，应先通过计划明确迁移方式，再执行。

## 2. 总体架构

```text
Vue 3 前端
  -> Spring Boot 后端
      -> MySQL 权威知识库
      -> LangChain4j / OpenAI-compatible client 调用本地 9B 模型
      -> RemoteRagClient 调用 Python RAG Service
          -> 文本清洗
          -> 章节切分
          -> chunk 构建
          -> Chroma 向量索引
          -> SQLite FTS 全文索引
          -> ChapterFact 抽取
          -> 混合检索
```

职责边界不能破坏：

| 模块 | 职责 |
| --- | --- |
| Spring Boot | 业务编排、权限、项目/书籍/章节/任务、SSE、聊天、引用、审核、评测记录 |
| Python RAG Service | 文本处理、切章、chunk、索引、抽取、检索、评测脚本 |
| MySQL | 权威业务数据和知识资产 |
| Chroma | 向量检索辅助层 |
| SQLite FTS | 关键词全文检索辅助层 |
| 本地 9B 模型 | 摘要、抽取、问答、草稿生成 |

## 3. 版本路线

### v1：最小生命线

目标：让一本 txt/md 小说从上传到可追溯问答完整跑通。

```text
上传书籍
-> 清洗文本
-> 切章节
-> 切 chunk
-> 建 Chroma / SQLite FTS 索引
-> 抽取 ChapterFact
-> 保存 MySQL
-> 创建 ChatSession
-> 单书问答
-> 返回答案和 Citation
-> SSE 展示构建和问答过程
```

v1 完成标准：

```text
三个服务能启动
MySQL / Chroma 能连接
书能导入
章节能切开
chunk 能生成
ChapterFact 能保存
AgentRun / AgentStep / ModelRun 能记录
检索能返回证据
问答能返回引用
前端三栏式工作台能展示过程
样例书和黄金问题能验证效果
```

### v2：知识资产沉淀与质量闭环

目标：把 v1 的“可问答”升级为“可审核、可沉淀、可评测”。

```text
EntityProfile 聚合
ReviewHarness 审核队列
Book Wiki 草稿和引用
EvalHarness 黄金问题评测
PromptVersion / RetrieverVersion 管理
轻量 EntityNode / EntityEdge 入口
```

v2 不做复杂多书问答、云同步、完整设定卡系统、复杂图数据库平台。

### v3+：扩展能力

```text
v3 多书联合问答
v4 设定卡系统
v5 云端同步和外部资料增强
v6 复杂知识图谱和关系推理
v7 协作审核与发布流程
```

## 4. 文档读取顺序

后续 agent 接任务前按以下顺序读取：

```text
1. NovelBridge-Agents 项目简介.md
2. NovelBridge-Agents Vibecoding 开发任务书 v1.md
3. NovelBridge-Agents 00 总Plan.md
4. NovelBridge-Agents 01 Harness Engineering 开发规范.md
5. NovelBridge-Agents 02 v1 详细开发计划.md
6. NovelBridge-Agents 03 v2 详细开发计划.md
7. NovelBridge-Agents 04 后续路线.md
8. NovelBridge-Agents 05 Agent任务模板与对抗检查.md
```

## 5. 执行节奏

```text
阶段 0：项目基线
阶段 1：基础业务模型
阶段 2：书籍导入
阶段 3：Python 文本清洗与章节切分
阶段 4：BookBuildHarness MVP
阶段 5：chunk 构建与索引
阶段 6：ChapterFact 抽取
阶段 7：基础混合检索
阶段 8：QueryAnswerHarness MVP
阶段 9：前端 AI 阅读工作台
阶段 10：样例、黄金问题与质量验证
```

每个阶段结束时必须留下可验证结果。禁止“代码看起来写完了，但没有样例、没有状态、没有引用、没有失败记录”。

## 6. 全局禁止项

```text
禁止把项目做成普通聊天 RAG
禁止让 Java 后端直接操作 Chroma
禁止让 Python 服务承担用户权限和业务管理
禁止绕过 AgentRun / AgentStep
禁止模型输出直接成为 APPROVED 知识
禁止 prompt 写死在业务代码里
禁止返回没有来源的权威知识
禁止第一版提前做复杂知识图谱、复杂 Book Wiki、多书问答、云同步
```

## 7. 总体验收

agent 完成任一阶段后，必须在交付说明中回答：

```text
改了哪些模块
新增了哪些接口
新增了哪些表或字段
如何启动
如何验证
哪些样例通过
失败时 errorMessage 在哪里看
哪些内容仍是草稿或预留
是否违反了职责边界
```

