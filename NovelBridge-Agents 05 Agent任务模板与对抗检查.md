# NovelBridge-Agents Agent任务模板与对抗检查

## 0. 使用方式

后续给 coding agent 分配任务时，直接复制本模板，并填入任务编号、目标、修改范围、接口和验收标准。agent 必须先读相关文档，再执行代码修改。

## 1. 标准任务模板

```text
你现在负责 NovelBridge-Agents 项目的【任务编号：Txx】。

项目定位：
NovelBridge-Agents 是单书知识资产构建与可追溯问答系统，不是普通聊天 RAG。

当前任务目标：
【填写本任务目标】

当前阶段：
【v1 / v2 / 后续版本】

必须先阅读：
1. NovelBridge-Agents 项目简介.md
2. NovelBridge-Agents Vibecoding 开发任务书 v1.md
3. NovelBridge-Agents 00 总Plan.md
4. 与当前阶段相关的详细开发计划

必须遵守：
1. 只实现当前任务，不提前实现后期功能。
2. 不随意更换技术栈。
3. Spring Boot 负责业务编排、权限、任务、SSE、聊天和引用。
4. Python RAG Service 负责文本处理、切章、chunk、索引、抽取和检索。
5. MySQL 是权威知识和业务库。
6. Chroma / SQLite FTS 是检索辅助层。
7. 所有长任务必须记录 AgentRun / AgentStep。
8. 所有模型调用必须记录 ModelRun。
9. 所有回答必须尽量保存 Citation。
10. 所有模型产物默认 DRAFT 或 AUTO_EXTRACTED，不能直接 APPROVED。
11. Prompt 必须版本化，不能写死在业务代码里。
12. 所有错误必须有可读 errorMessage。

需要修改的目录：
【填写目录】

需要实现的接口：
【填写接口】

需要新增或调整的数据对象：
【填写对象】

验收标准：
【填写验收标准】

测试要求：
【填写测试命令、样例、手工验证路径】

交付说明必须包含：
1. 改了哪些文件
2. 新增了哪些接口
3. 新增了哪些表或字段
4. 如何启动
5. 如何验证
6. 失败时 errorMessage 在哪里查看
7. 有没有遗留风险
```

## 2. v1 任务拆分模板

### T0 项目基线

```text
目标：三个服务和基础环境能启动。
修改范围：项目根目录、后端配置、frontend、rag-service、docker、data、README。
验收：后端 health、前端首页、Python health、MySQL、Chroma 均可验证。
```

### T1 基础业务模型

```text
目标：核心实体和可追踪任务模型落地。
修改范围：backend。
验收：核心表可创建，Project / Folder / Book / ChatSession 可 CRUD，AgentRun / AgentStep / ModelRun / Citation 可保存。
```

### T2 书籍导入

```text
目标：上传 txt/md 并创建 Book。
修改范围：backend、data/books。
验收：合法文件成功，非法文件失败，Book.status = IMPORTED，不暴露真实路径。
```

### T3 Python 切章

```text
目标：Python 服务完成清洗和章节切分。
修改范围：rag-service。
验收：两个 sample 可正确切章，pytest 通过。
```

### T4 BookBuildHarness MVP

```text
目标：后端编排切章、保存 Chapter、推送 SSE。
修改范围：backend、rag-service client。
验收：AgentRun / AgentStep 完整，失败可追踪，SSE 有结构化事件。
```

### T5 chunk 与索引

```text
目标：chunk 生成并建立 Chroma / SQLite FTS。
修改范围：backend、rag-service。
验收：chunk 保存 MySQL，Chroma 和 FTS 可检索。
```

### T6 ChapterFact

```text
目标：每章生成结构化事实草稿。
修改范围：backend、rag-service、docs/prompts。
验收：ChapterFact 可解析、可保存、ModelRun 可追踪、status = AUTO_EXTRACTED。
```

### T7 混合检索

```text
目标：问题可检索 ChapterFact 和 chunk。
修改范围：rag-service。
验收：返回 sourceType、chapterId、chunkId/factId、evidenceText、score。
```

### T8 QueryAnswerHarness

```text
目标：单书问答可保存消息、答案、引用、问题索引。
修改范围：backend、rag-service query client、llm client。
验收：ChatMessage / Citation / ChatQuestionIndex / AgentRun / ModelRun 完整。
```

### T9 前端工作台

```text
目标：三栏式 AI 阅读工作台。
修改范围：frontend。
验收：左侧书籍和对话，中间问答，右侧问题索引和引用，SSE 过程展示。
```

### T10 质量验证

```text
目标：样例和黄金问题验证 v1。
修改范围：data/samples、tests、README。
验收：样例书完整构建，黄金问题命中相关章节，引用可追溯。
```

## 3. 对抗思考清单

开发前检查：

```text
这个任务是否属于当前阶段？
是否需要 AgentRun / AgentStep？
是否涉及模型调用和 ModelRun？
是否涉及回答和 Citation？
是否需要 promptVersion？
是否会破坏 Spring Boot / Python 的职责边界？
是否提前实现了后期功能？
```

开发中检查：

```text
失败路径是否记录 errorMessage？
状态流转是否明确？
接口返回是否统一？
是否有路径穿越或真实路径泄露？
是否把 prompt 写死进代码？
是否把模型输出当成权威知识？
```

交付前检查：

```text
是否能通过样例验证？
是否有测试或手工验收步骤？
是否能复盘一次模型调用？
是否能复盘一次长任务？
是否能追溯一次回答引用？
是否清楚说明了未完成和预留内容？
```

## 4. 常见错误

```text
错误：先做一个聊天页，再慢慢补引用。
正确：问答从第一天就保存 ChatMessage、Citation、QuestionIndex。

错误：Python 直接写 MySQL。
正确：Python 返回结构化结果，Java 后端负责编排和权威保存。

错误：Java 后端直接写 Chroma。
正确：Java 调用 Python RAG Service，Python 管索引。

错误：模型抽取结果直接 APPROVED。
正确：默认 AUTO_EXTRACTED，v2 通过 ReviewHarness 审核。

错误：prompt 写在 Service 字符串里。
正确：prompt 文件化、版本化，ModelRun 记录 promptVersion。

错误：只测试接口能返回 200。
正确：验证数据、状态、引用、错误路径和样例效果。
```

