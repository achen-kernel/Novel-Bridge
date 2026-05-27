# NovelBridge 双 Agent 实施计划 v0.1

本文档整理 `docs/11-agent-architecture-brief.md` 与 `docs/GPT/` 两份规划回复，目标是把后续开发收敛为可执行路线。

当前结论：先不重写已有 P1-P8、QA、Quality、Eval、UI，而是在现有能力外层补一套共享 Agent Runtime，再逐步把两个 Agent 接入。

## 1. 总体方向

NovelBridge 后续采用两个 Agent：

| Agent | 定位 | 主要职责 |
|---|---|---|
| `PreprocessAgent` | 离线知识构建 Agent | 编排文本导入、切章、切块、抽取、治理、索引、质量检查、导出 |
| `ReaderAgent` | 在线阅读/分析/反哺 Agent | 问答、线索追踪、设定/伏笔/关系/风格分析、知识库补全建议 |

共享能力放在 `app/agent_runtime/`：

- 状态机
- Action/Tool 注册与执行
- Context 加载
- Evidence/Citation 校验
- AgentRun/AgentStep/ToolCall/ModelCall 记录
- 检索轨迹与调试信息

设计原则：

- Python-first。Agent、RAG、模型调用、质量流程继续以 Python 为主。
- Java 后续只承担产品 API、业务聚合、权限/会话/进度推送等偏业务层职责。
- LLM Planner 只能提出下一步候选动作；真实状态转移、工具执行、写库权限由 Python 状态机控制。
- 模型输出永远是候选数据，不是真值。
- Qdrant 继续作为主向量库，Neo4j 只作为验证后事实的图投影。

## 2. 接受的设计决策

### 2.1 命名与边界

采用以下命名：

- `PreprocessAgent`
- `ReaderAgent`
- `app/agent_runtime/`
- `app/context_store/`
- `app/knowledge_patch/`

保留现有 `app/qa/` 作为问答服务层。后续 `ReaderAgent` 的 `answer` mode 调用它，而不是直接替换它。

### 2.2 状态机优先

每个 Agent 都必须有代码层状态机。Prompt 中可以描述规则，但不能依赖 Prompt 保证流程正确。

`PreprocessAgent` 初始状态建议：

```text
NEW
-> SOURCE_REGISTERED
-> SOURCE_DECODED
-> CHAPTERS_SPLIT
-> CHUNKS_BUILT
-> PRIOR_READY
-> MENTIONS_EXTRACTED
-> CHAPTER_FACTS_BUILT
-> ENTITIES_GOVERNED
-> FACTS_AGGREGATED
-> QUALITY_CHECKED
-> INDEXED
-> GRAPH_PROJECTED
-> DATASET_EXPORTED
-> DONE
```

任意状态可进入：

```text
NEED_REVIEW / FAILED / CANCELED
```

`ReaderAgent` 初始状态建议：

```text
NEW_TASK
-> INTENT_CLASSIFIED
-> SCOPE_RESOLVED
-> PLAN_READY
-> CONTEXT_ROUTED
-> CONTEXT_LOADED
-> EVIDENCE_SEARCHING
-> EVIDENCE_COLLECTED
-> DRAFT_READY
-> VERIFIED
-> RESPONDED
```

知识反哺分支：

```text
PATCH_DRAFTED
-> PATCH_VALIDATED
-> PATCH_PENDING_REVIEW
```

任意状态可进入：

```text
NEED_FOLLOWUP / INSUFFICIENT_EVIDENCE / FAILED / CANCELED
```

### 2.3 ReaderAgent 必须按 mode 拆分

`ReaderAgent` 不应一次性做成大而全系统。按 mode 渐进：

| 阶段 | Mode | 目标 |
|---|---|---|
| A | `answer` | 替代当前 QA 页面背后的流程编排，但复用现有 QA 检索/回答能力 |
| A/B | `analyze` | 人物、关系、章节、设定的证据化分析 |
| B | `trace` | 伏笔、物件、能力、设定、人物关系的跨章节追踪 |
| B | `enrich` | 提出知识库补全建议，生成 KnowledgePatch |
| C | `learn_style` | 描写、叙事节奏、风格样本学习 |
| C | `authoring` | 面向创作辅助，必须建立在已验证知识与风格样本之上 |

早期只实现 `answer` 和最小 `analyze`。

### 2.4 ContextStore 是路由层，不是真值层

借鉴 OpenViking 的 L0/L1/L2 分层，但必须适配 NovelBridge 的证据优先规则：

| 层级 | 用途 | 是否可作为事实引用 |
|---|---|---|
| L0 | 低 token 摘要，用于路由和快速判断范围 | 否 |
| L1 | 结构化要点，用于候选上下文召回 | 否 |
| L2 | 原文 chunk、ChapterFact、citation、validated relation/event | 是 |

L0/L1 可以帮助 Agent 决定去哪查，但最终回答和补丁都必须回到 L2 证据。

建议 URI 风格：

```text
nb://book/{book_id}
nb://book/{book_id}/chapter/{chapter_id}
nb://book/{book_id}/entity/{entity_id}
nb://book/{book_id}/relation/{relation_id}
nb://book/{book_id}/event/{event_id}
nb://book/{book_id}/style/{style_sample_id}
```

### 2.5 KnowledgePatch 只做候选，不直接写正式知识库

ReaderAgent 可以提出补丁，但不能直接合并到正式表。

建议补丁流程：

```text
PROPOSED
-> SCHEMA_VALIDATED
-> AUTO_VALIDATED
-> PENDING_REVIEW
-> ACCEPTED
-> MERGED
```

拒绝或挂起状态：

```text
REJECTED / NEEDS_MORE_EVIDENCE / SUPERSEDED
```

早期支持的 Patch 类型：

| 类型 | 风险 | 说明 |
|---|---|---|
| `citation_fix` | 低 | 修正或补充引用 |
| `context_summary_update` | 低 | 更新 L0/L1 摘要 |
| `event_add` | 中 | 提议新增事件 |
| `relation_stage_add` | 中 | 提议新增阶段性关系 |
| `setting_update` | 中 | 提议新增或修正设定 |
| `foreshadowing_link` | 中 | 提议建立伏笔与回收关系 |
| `alias_add` | 高 | 提议新增别名 |
| `alias_block` | 高 | 提议禁止错误别名合并 |
| `entity_split` | 极高 | 提议拆实体 |
| `entity_merge` | 极高 | 提议合并实体 |

早期不做自动 merge，尤其不能自动执行 `entity_merge` / `entity_split`。

## 3. 暂缓或拒绝的事项

以下内容有价值，但不进入第一批实现：

- 直接替换现有 P1-P8 pipeline。
- 把 Neo4j 作为主检索入口。
- 让 ReaderAgent 自动修改正式实体、关系、事件表。
- 一次性创建所有高级叙事模型表。
- Java 侧引入 Spring AI、Qdrant client、Neo4j driver。
- 把 ContextStore 做成第二事实库。

高级叙事对象先写 contract，不急于建表：

- `ForeshadowingThread`
- `SettingThread`
- `RelationStage`
- `StyleSample`
- `NarrativeDriver`
- `PovObservation`
- `ContinuityIssue`
- `CharacterArc`
- `ItemLifecycle`
- `AbilityLifecycle`
- `SceneFunction`
- `GenreProfile`

## 4. 分阶段实施

### Stage 0：文档与边界收敛

目标：先统一概念，不改核心逻辑。

建议新增/更新：

- `docs/12-agent-implementation-plan.md`：本文档。
- `docs/13-reader-agent-contract.md`：ReaderAgent 输入输出、mode、状态机、API 草案。
- `docs/14-knowledge-patch-contract.md`：KnowledgePatch schema、状态、权限、审核流程。
- `docs/04-agent-runtime.md`：补充共享运行时设计。
- `docs/qa-agent-design.md`：调整为 ReaderAgent answer mode 的设计来源，而不是独立大系统。
- `docs/06-rag-strategy.md`：补充 ContextStore L0/L1/L2 与检索轨迹。
- `AGENTS.md`：补充双 Agent 目标和 Python-first / Java-later 边界。

完成标准：

- 名称统一。
- Java/Python 边界统一。
- ReaderAgent 不再被描述为只做 QA。
- KnowledgePatch 明确为候选层。

### Stage A1：最小共享 Agent Runtime

目标：提供两个 Agent 共用的运行骨架。

建议目录：

```text
apps/rag-agent/app/agent_runtime/
├── __init__.py
├── actions.py
├── citation_verifier.py
├── context_manager.py
├── evidence.py
├── model_call_store.py
├── model_provider.py
├── planner.py
├── run_store.py
├── schemas.py
├── state_machine.py
├── tool_executor.py
├── tool_registry.py
└── trace_store.py
```

第一批只实现：

- 状态枚举与转移校验。
- Action schema。
- Tool registry。
- AgentRun/AgentStep 读写适配。
- ModelCall 记录适配。
- Citation verifier 的最小接口。
- Retrieval trace 的最小接口。

数据层：

- 优先复用已有 `novel_agent_run`、`novel_agent_step`、`novel_model_call`。
- 若缺少工具调用记录，再新增 `novel_tool_call`。
- 若现有 model call 表字段不够，先加兼容字段，不另起平行系统。

测试：

```text
apps/rag-agent/tests/agent_runtime/
```

覆盖：

- 合法状态转移。
- 非法状态转移被拒绝。
- Planner 输出无法直接绕过状态机。
- Tool 调用必须记录。

### Stage A2：PreprocessAgent 包装现有 Pipeline

目标：把 P1-P8 变成可观测、可恢复、可审核的 Agent 流程。

建议目录：

```text
apps/rag-agent/app/preprocess_agent/
├── __init__.py
├── agent.py
├── actions.py
├── schemas.py
└── states.py
```

实现方式：

- 不重写 `app/pipeline/`。
- 每个 Action 包装一个或一组已有 pipeline service。
- 每步写 AgentStep。
- 每个模型调用继续写 ModelCall。
- 长任务失败后能通过状态判断可恢复点。

优先包装：

- 书籍注册与编码处理。
- 切章/切块。
- ChapterFact 生成。
- Entity governance。
- Qdrant index。
- Quality workflow。

API 可后置，先保证内部可调用。

### Stage A3：ReaderAgent answer mode

目标：用 Agent 流程重构当前 QA 编排，但复用现有 `app/qa` 能力。

建议目录：

```text
apps/rag-agent/app/reader_agent/
├── __init__.py
├── agent.py
├── modes/
│   ├── __init__.py
│   └── answer.py
├── schemas.py
└── states.py
```

建议 API：

```text
POST /api/reader-agent/run
GET  /api/reader-agent/runs/{run_id}
GET  /api/reader-agent/runs/{run_id}/trace
```

早期请求：

```json
{
  "mode": "answer",
  "book_id": 6,
  "question": "孙悟空为什么三打白骨精？",
  "session_id": null,
  "options": {
    "provider": "local",
    "require_citations": true
  }
}
```

早期返回：

```json
{
  "run_id": 123,
  "mode": "answer",
  "status": "RESPONDED",
  "answer": "...",
  "citations": [],
  "evidence": [],
  "trace_id": 456,
  "patches": []
}
```

必须保留旧 QA API，避免 UI 与评测一次性迁移。

### Stage A4：ContextStore L0/L1/L2

目标：降低长上下文成本，提高检索可观测性。

建议目录：

```text
apps/rag-agent/app/context_store/
├── __init__.py
├── builder.py
├── retriever.py
├── schemas.py
└── store.py
```

建议数据对象：

- `novel_context_node`
- `novel_context_edge`
- Qdrant collection：`nb_context_l1`

约束：

- L0/L1 只能用于路由和候选召回。
- 回答必须引用 L2。
- L0/L1 必须记录来源版本：`book_id`、`chapter_id`、`source_hash`、`pipeline_version`、`prompt_version`、`schema_version`、`rules_version`。

先从 book/chapter/entity 三类节点开始，不要一次性铺满高级对象。

### Stage A5：KnowledgePatch propose-only

目标：让 ReaderAgent 可以反哺知识库，但所有正式写入都经过候选补丁与审核。

建议目录：

```text
apps/rag-agent/app/knowledge_patch/
├── __init__.py
├── schemas.py
├── validator.py
├── store.py
└── service.py
```

建议 API：

```text
GET  /api/knowledge-patches
GET  /api/knowledge-patches/{patch_id}
POST /api/knowledge-patches/{patch_id}/review
```

早期只做：

- schema 校验。
- evidence 绑定。
- 风险分级。
- review 状态流转。

不做：

- 自动 merge。
- 复杂冲突解决。
- 大规模表结构变更。

## 5. 与现有代码的集成点

### 5.1 Pipeline

现有 `app/pipeline/` 是 `PreprocessAgent` 的工具层，不应被 Agent 重写。

需要补充：

- Pipeline step 到 Agent state 的映射。
- 每步输入输出 artifact 的记录。
- 失败状态与可恢复点。

### 5.2 QA

现有 `app/qa/` 是 `ReaderAgent.answer` 的服务层。

需要补充：

- Intent/scope 解析。
- 检索轨迹。
- Citation verifier。
- 证据不足时的明确失败状态。
- 会话记忆只影响上下文路由，不能替代证据。

### 5.3 Eval

现有 37 个 eval case 继续保留。

需要扩展：

- 对 ReaderAgent answer mode 增加 eval 入口。
- 增加引用正确性、证据覆盖、拒答正确性、检索轨迹完整性指标。
- 后续从用户反馈生成 eval case candidate。

### 5.4 Quality

现有 `quality/` 继续作为数据修复工具层。

需要补充：

- 质量问题可以生成 KnowledgePatch candidate。
- 高风险实体治理必须保留人工审核。

### 5.5 API

新增 Agent API 时必须不破坏现有 UI：

- 旧 `/qa` 页面继续可用。
- 新 ReaderAgent API 先供开发和调试使用。
- Java 后续可以代理 Python API，但当前不要求迁移。

## 6. 版本与可恢复性

后续新增数据必须保留版本信息，至少包含：

- `text_hash`
- `pipeline_version`
- `prompt_version`
- `schema_version`
- `rules_version`
- `model_provider`
- `model_name`

目标：

- 同一章节可以知道由哪个 pipeline/prompt/schema 生成。
- 后续 Prompt 改动后能判断哪些数据需要重跑。
- ReaderAgent 的回答能追溯到检索轨迹与证据版本。

## 7. 当前最小下一步

建议按以下顺序推进：

1. 完成 Stage 0 文档收敛。
2. 新增 `docs/13-reader-agent-contract.md`。
3. 新增 `docs/14-knowledge-patch-contract.md`。
4. 更新 `docs/04-agent-runtime.md`，把共享 runtime 写成正式项目设计。
5. 更新 `docs/qa-agent-design.md`，将其定位为 ReaderAgent answer/analyze 的来源文档。
6. 开始 Stage A1：实现最小 `app/agent_runtime/`。

不建议现在直接写 ReaderAgent 大功能。先把 runtime、状态机、记录、工具调用、引用校验骨架定住。

## 8. 仍需确认的问题

这些问题应在实现 Stage A1/A3 前确认：

1. 现有 `novel_agent_run`、`novel_agent_step`、`novel_model_call` 字段是否足够支撑 Agent Runtime。
2. 是否已有工具调用表；如果没有，`novel_tool_call` 应放入哪份 migration。
3. ReaderAgent API 是否直接暴露给前端，还是先做内部调试端点。
4. KnowledgePatch review UI 是先放 Python Browse UI，还是等 Java 产品 API 接管。
5. ContextStore L1 是否使用独立 Qdrant collection `nb_context_l1`，还是先复用现有 collection 并用 payload 区分。
6. 对实体合并/拆分的审核标准是否需要先写成单独治理文档。

## 9. Codex 后续执行提示

后续让 Codex 继续开发时，可使用如下任务边界：

```text
请先阅读 AGENTS.md、docs/12-agent-implementation-plan.md、docs/04-agent-runtime.md、docs/qa-agent-design.md。
不要读取 docs/private/ 和 docs/_archive/。
本次只做 Stage A1：新增最小 app/agent_runtime/ 骨架，复用现有表和代码，不接入 ReaderAgent 大功能。
实现状态机、Action schema、Tool registry、Run/Step/ModelCall 适配层和最小测试。
不要改现有 QA 行为，不要新增高级叙事表，不要自动写正式知识库。
```
