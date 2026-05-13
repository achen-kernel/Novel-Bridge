# NovelBridge-Agents v2 详细开发计划

## 0. v2 定位

v2 的目标是把 v1 的“能导入、能检索、能问答”升级为“能沉淀、能审核、能评测”。v2 仍然围绕单书，不做复杂多书问答、云同步或大型图数据库平台。

```text
v1：Book Memory Package 的最小生命线
v2：Book Memory Package 的质量闭环
```

## 1. v2 入口条件

只有 v1 达到以下状态后，才开始 v2：

```text
书籍可导入
章节可切分
chunk 可生成
ChapterFact 可保存
单书问答可返回引用
AgentRun / AgentStep / ModelRun / Citation 已落库
SSE 构建和问答过程可展示
样例书和黄金问题可运行
```

如果 v1 的可追溯链路不完整，禁止开始 v2。

## 2. 阶段 V2-1：EntityProfile 聚合

### 目标

从 ChapterFact 中聚合人物、地点、物品、组织、事件等实体草稿。

### 新增对象

```text
EntityProfile
EntityAlias
EntityMention
```

### 行为

```text
从 ChapterFact.characters / locations / items / events 聚合实体候选
保留每个实体的 mention 来源
别名合并必须保留置信度和证据
EntityProfile.status 默认 AUTO_EXTRACTED
低置信合并进入 NEED_FIX
```

### 接口建议

```text
POST /api/books/{bookId}/entities/build
GET  /api/books/{bookId}/entities
GET  /api/entities/{entityId}
GET  /api/entities/{entityId}/mentions
```

### 验收

```text
一本书能生成 EntityProfile 草稿
每个实体能追溯到章节和 evidenceText
别名合并不覆盖原始 mention
实体不能自动 APPROVED
```

### 对抗检查

```text
是否把实体聚合做成了不可追溯的名称列表？
是否把同名不同人强行合并？
是否丢失 alias 来源？
```

## 3. 阶段 V2-2：ReviewHarness

### 目标

建立人工审核队列，把 AI 草稿升级为权威知识。

### 新增对象

```text
ReviewItem
ReviewDecision
```

### 支持对象

```text
ChapterFact
EntityProfile
BookWikiPage
SettingCard 预留
```

### 状态流转

```text
AUTO_EXTRACTED -> REVIEWING -> APPROVED
AUTO_EXTRACTED -> REVIEWING -> REJECTED
AUTO_EXTRACTED -> REVIEWING -> NEED_FIX
DRAFT -> REVIEWING -> APPROVED
```

### 接口建议

```text
POST /api/review-items
GET  /api/review-items
GET  /api/review-items/{reviewItemId}
POST /api/review-items/{reviewItemId}/approve
POST /api/review-items/{reviewItemId}/reject
POST /api/review-items/{reviewItemId}/need-fix
```

### 验收

```text
可创建审核项
审核项能展示来源证据
approve 后原对象状态变为 APPROVED
reject 和 need-fix 必须记录原因
审核日志可追踪 reviewerId 和时间
```

### 对抗检查

```text
是否没有人工动作就 APPROVED？
是否审核后丢失模型原始输出？
是否没有 reject 原因？
```

## 4. 阶段 V2-3：Book Wiki 草稿

### 目标

基于 ChapterFact、EntityProfile 和引用证据，生成可审核的 Book Wiki 草稿。

### 新增对象

```text
BookWikiPage
BookWikiCitation
```

### Wiki 类型

```text
CHAPTER_OVERVIEW
CHARACTER_PROFILE
LOCATION_PROFILE
ITEM_PROFILE
EVENT_TIMELINE
WORLD_RULE
```

### 行为

```text
WikiPage 初始状态 DRAFT 或 AUTO_EXTRACTED
每段关键内容必须关联 BookWikiCitation
Wiki 生成必须记录 ModelRun
Wiki 不替代 ChapterFact，而是知识资产展示层
```

### 接口建议

```text
POST /api/books/{bookId}/wiki-pages/generate
GET  /api/books/{bookId}/wiki-pages
GET  /api/wiki-pages/{pageId}
PUT  /api/wiki-pages/{pageId}
GET  /api/wiki-pages/{pageId}/citations
```

### 验收

```text
能生成章节概览草稿
能生成角色档案草稿
每个 Wiki 页面有 citation
Wiki 页面可进入 ReviewHarness
```

### 对抗检查

```text
是否生成无引用百科文本？
是否把 Wiki 当作权威来源覆盖原始证据？
```

## 5. 阶段 V2-4：EvalHarness

### 目标

用黄金问题验证章节切分、检索、引用和问答质量。

### 新增对象

```text
EvalCase
EvalResult
PromptVersion
RetrieverVersion
```

### 评测维度

```text
chapterHit：是否命中正确章节
chunkHit：是否命中正确片段
citationValid：引用是否存在且可追溯
answerGrounded：回答是否被证据支持
refusalQuality：证据不足时是否承认不足
```

### 接口建议

```text
POST /api/eval-cases
GET  /api/books/{bookId}/eval-cases
POST /api/eval-runs
GET  /api/eval-runs/{evalRunId}
GET  /api/eval-runs/{evalRunId}/results
```

### 验收

```text
可维护黄金问题
可运行一次评测
可对比 promptVersion / retrieverVersion
失败结果有 failureReason
评测不要求自动打满分，但必须保留证据命中信息
```

### 对抗检查

```text
是否只评估回答文字，不评估引用？
是否无法比较不同 prompt 和检索版本？
```

## 6. 阶段 V2-5：PromptVersion 与 RetrieverVersion

### 目标

让 prompt 和检索策略变化可追踪、可回滚、可评测。

### 行为

```text
prompt 文件放在 docs/prompts
PromptVersion 记录 name、version、filePath、checksum、description、active
RetrieverVersion 记录 name、version、strategyConfigJson、description、active
ModelRun 必须引用 promptVersion
Query AgentRun 必须引用 retrieverVersion
```

### 验收

```text
可查看当前激活 prompt
可查看当前激活检索策略
历史 ModelRun 可追溯到当时版本
EvalResult 可比较版本差异
```

### 对抗检查

```text
是否 prompt 仍散落在代码中？
是否检索参数改动无法追溯？
```

## 7. 阶段 V2-6：轻量知识图谱入口

### 目标

提供轻量 EntityNode / EntityEdge，为后续图谱打基础，但不构建复杂图数据库。

### 新增对象

```text
EntityNode
EntityEdge
```

### 行为

```text
Node 来源于 APPROVED 或 REVIEWING 的 EntityProfile
Edge 来源于 ChapterFact.relationships 或审核后的关系
Edge 必须有 evidenceText
图谱仅用于展示和辅助检索，不作为 v2 推理核心
```

### 接口建议

```text
POST /api/books/{bookId}/graph/build
GET  /api/books/{bookId}/graph
GET  /api/entities/{entityId}/edges
```

### 验收

```text
能展示实体关系
关系能追溯 evidenceText
图谱构建不影响 v1 问答主链路
```

### 对抗检查

```text
是否提前引入复杂图数据库？
是否生成没有证据的关系边？
```

## 8. v2 最终验收

```text
EntityProfile 可从 ChapterFact 聚合
ReviewHarness 可审核 ChapterFact / EntityProfile / Wiki 草稿
Book Wiki 页面有 citation
EvalHarness 可运行黄金问题
PromptVersion / RetrieverVersion 可追踪
轻量图谱可展示但不侵入主链路
所有 APPROVED 内容都有人工审核或明确审核记录
```

