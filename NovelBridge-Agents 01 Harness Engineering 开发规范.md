# NovelBridge-Agents Harness Engineering 开发规范

## 0. 核心立场

本项目的核心不是模型能力，而是 Harness Engineering。模型只负责“读、抽、写、答”，Harness 负责把模型放进可追踪、可审核、可重试、可评测的工程流程中。

任何 agent 开发功能前，先判断当前工作属于哪个 Harness：

```text
BookBuildHarness：从原始书籍构建单书知识资产
QueryAnswerHarness：基于证据完成单书问答
ReviewHarness：把 AI 草稿变成人工审核后的知识资产
EvalHarness：评估模型、prompt、检索策略和版本变化
```

## 1. Harness 通用规则

所有 Harness 都必须遵守：

```text
1. 输入必须可定位
2. 输出必须可追溯
3. 每个步骤必须有状态
4. 每次模型调用必须可复盘
5. 每次失败必须有 errorMessage
6. 可重试步骤不能污染已成功数据
7. AI 产物默认不是权威知识
8. 对用户展示的关键结论必须尽量有 Citation
```

通用状态：

```text
TaskStatus: PENDING, RUNNING, SUCCESS, FAILED, CANCELED, PARTIAL_SUCCESS
StepStatus: WAITING, RUNNING, SUCCESS, FAILED, RETRYING, SKIPPED
ContentStatus: DRAFT, AUTO_EXTRACTED, REVIEWING, APPROVED, REJECTED, NEED_FIX
BookStatus: IMPORTED, BUILDING, READY_FOR_QA, BUILD_FAILED, NEED_REVIEW, ARCHIVED
```

## 2. BookBuildHarness

### 2.1 目标

把一本 txt/md 小说构建为可长期使用的 Book Memory Package。

### 2.2 输入

```text
bookId
sourcePath
projectId
folderId
userId
buildOptions
```

### 2.3 输出

```text
Book status
Chapter[]
Chunk[]
ChapterFact[]
AgentRun
AgentStep[]
ModelRun[]
Index build result
SSE build events
```

### 2.4 标准步骤

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
```

每个步骤都要对应一条 `AgentStep`。如果某一步由 Python 服务完成，Java 后端仍负责创建和更新步骤状态。

### 2.5 失败处理

```text
文本读取失败：Book -> BUILD_FAILED，记录 sourcePathRef 和 errorMessage
章节切分失败：保留 Book，失败 AgentStep 记录 Python 返回信息
chunk 构建失败：不可进入 READY_FOR_QA
索引失败：允许标记 PARTIAL_SUCCESS，但必须明确 vectorIndexStatus / ftsIndexStatus
ChapterFact 抽取失败：章节仍可保存，ChapterFact 可缺失或 NEED_FIX，但必须记录 ModelRun
```

### 2.6 不允许

```text
不允许 Python 直接写 MySQL 权威表
不允许 Java 直接写 Chroma
不允许跳过章节保存直接构建问答
不允许没有 AgentRun 就执行构建
不允许 ChapterFact 无状态保存
```

## 3. QueryAnswerHarness

### 3.1 目标

基于一本书的 ChapterFact 和 chunk，回答用户问题并返回可追溯引用。

### 3.2 输入

```text
sessionId
bookId
questionText
userId
retrieverVersion
promptVersion
```

### 3.3 输出

```text
User ChatMessage
Assistant ChatMessage
ChatQuestionIndex
Citation[]
AgentRun
AgentStep[]
ModelRun
SSE query events
```

### 3.4 标准步骤

```text
QUERY_RECEIVED
INTENT_DETECTED
RETRIEVAL_STARTED
RETRIEVAL_FINISHED
CONTEXT_BUILT
LLM_ANSWERING
CITATION_VALIDATED
ANSWER_FINISHED
```

v1 的 `INTENT_DETECTED` 可以是简单占位，不做复杂意图识别。不能因此跳过 AgentStep。

### 3.5 引用规则

回答中的 Citation 至少要能追溯到：

```text
bookId
chapterId
chapterNo
chunkId 或 factId
sourceType: CHUNK / CHAPTER_FACT
evidenceText
score
```

如果模型生成了无法被 evidence 支撑的结论，回答中应标注“根据当前检索证据不足”，而不是伪造引用。

### 3.6 不允许

```text
不允许只把用户问题丢给模型
不允许回答没有保存 ChatMessage
不允许有答案但没有 Citation 记录
不允许把模型回答写入 Book Wiki 或 EntityProfile 的 APPROVED 数据
```

## 4. ReviewHarness

### 4.1 目标

把 `AUTO_EXTRACTED` 或 `DRAFT` 内容变成 `APPROVED` 权威知识。

### 4.2 v2 输入

```text
sourceObjectType: ChapterFact / EntityProfile / BookWikiPage / SettingCard
sourceObjectId
draftContent
evidenceRefs
reviewerId
```

### 4.3 v2 输出

```text
ReviewItem
reviewStatus
approvedContent
auditTrail
```

### 4.4 审核原则

```text
APPROVED 必须来自人工确认或明确审核动作
REJECTED 必须保留原因
NEED_FIX 必须指出缺失证据或内容问题
审核前后都要保留原始模型输出引用
```

## 5. EvalHarness

### 5.1 目标

让每次 prompt、模型、切分、检索策略改动都能被样例和黄金问题验证。

### 5.2 v2 输入

```text
evalCaseId
bookId
question
expectedEvidence
expectedAnswerPoints
promptVersion
retrieverVersion
modelName
```

### 5.3 v2 输出

```text
EvalResult
answerText
hitChapters
hitChunks
citationPrecision
answerScore
failureReason
```

### 5.4 评测原则

```text
评测不追求模型“说得好听”
优先检查是否命中正确章节、是否有引用、是否承认证据不足
检索策略变化必须能对比旧版本
prompt 变化必须有版本号
```

## 6. 对抗检查

任一 Harness 开发完成前，agent 必须自问：

```text
这个功能是否绕过了 AgentRun / AgentStep？
这个模型输出是否缺少来源？
这个失败是否能被用户或开发者定位？
这个状态是否能支持重试？
这个接口是否泄露了本地真实路径？
这个设计是否让 Python 承担了业务权限？
这个设计是否让 Java 直接控制了 Chroma？
这个功能是否提前实现了后期复杂能力？
```

