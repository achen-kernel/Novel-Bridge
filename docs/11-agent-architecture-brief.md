# NovelBridge 双 Agent 架构规划简报

> 目的：这份文档是给更强推理模型做深度规划用的上下文简报。它不要求一次性给出完整最终方案，而是希望模型基于 NovelBridge 当前状态、AI Reader 经验、coding agent 设计模式和 agent memory 思路，帮助我们规划两个核心 Agent 的长期架构与短期落地路线。
>
> 当前日期：2026-05-23
>
> 重要限制：不要读取 `docs/private/` 和 `docs/_archive/`。旧 `docs/pack/`、`docs/learn/` 可能有历史信息，但当前权威入口是 `AGENTS.md`、`docs/00-10`、本文件和 `docs/AI Reader/`。

## 1. 我们想让 GPT 帮忙回答什么

请不要只设计一个“问答机器人”。我们希望最终设计出两个长期可演进的 Agent：

1. **数据预处理 / 知识构建 Agent**
   - 离线运行。
   - 负责把小说从原文变成可检索、可审计、可反哺的结构化知识库。
   - 当前已有 P1-P8 pipeline，可以复用，不要推倒重写。

2. **阅读 / 分析 / 创作辅助 Agent**
   - 在线交互运行。
   - 问答只是其中一个 mode。
   - 未来还要支持：知识库反哺、伏笔链追踪、设定抽取与演化、人物/关系/物品/地点分析、描述描写学习、文风学习、作者视角辅助、后续创作辅助。

希望 GPT 重点输出：

- 两个 Agent 的职责边界、命名、模块划分。
- 是否应把现在的 `QA Agent` 重命名为更大的 `ReaderAgent` / `NarrativeAgent` / `AuthoringAgent`。
- 两个 Agent 是否共享一个通用 runtime：状态机、工具注册、上下文管理、ModelCall 记录、AgentRun/AgentStep 追踪。
- 每个 Agent 的核心状态机应该怎么设计。
- 每个 Agent 的工具集应该怎么设计，哪些工具短期必须做，哪些后续再做。
- 如何借鉴 coding agent 的 plan/act/observe/verify、workspace state、diff/patch、test feedback、task memory。
- 如何借鉴 OpenViking 这类 context database 的分层记忆，不一定要接入外部项目，但要吸收 L0/L1/L2、路径式上下文、递归检索、检索轨迹可观测、自我归档等思路。
- 如何让 Agent 反哺知识库但不污染 truth tables：候选 patch、证据、审核、merge 流程该怎么设计。
- 哪些 schema/table/store 需要新增或调整。
- 短期最小可行阶段应该如何切，避免一上来做全能 Agent。

我们最关心的不是“酷功能列表”，而是一个可维护、可评估、可恢复、可逐步扩展的工程架构。

## 2. 当前项目背景

NovelBridge 是一个 API-first 的小说阅读与作者分析 Agent 系统。

核心路线：

```text
Book -> Chapter -> Chunk -> ChapterFact -> Evidence/Citation
     -> Entity Governance -> Retrieval QA -> Narrative Graph -> Audit/Dataset
```

当前阶段是 Stage 3：QA + Quality + UI。

Python 是当前主线：

```text
apps/rag-agent/app/
├── api/          HTTP routes: books, browse, eval, facts, frontend, health, pipeline_api, qa
├── pipeline/     P1-P8 pipeline implementation
├── qa/           qa_runner, retrieval_runner, graph_query_runner
├── eval/         37 case eval runner/store
├── quality/      entity normalizer, relation deduper, event summarizer
├── clients/      MySQL, Qdrant, Neo4j, DeepSeek, llama-server, embedding
├── stores/       MySQL data access layer
├── schemas/
├── rules/
├── validators/
├── utils/
└── prompts/
```

Java `Novel-Bridge/` 已经存在 Spring Boot product API shell，能编译，包含 controllers/services/mappers/entities/VO/Flyway/health/rag-agent proxy。但当前策略是：

- 近期继续 Python-first。
- Agent runtime、pipeline、retrieval、model calls、eval、quality workflow 继续在 Python。
- Java 后续只承接偏业务/产品 API：上传入口、任务状态、chat/review API、前端聚合、SSE/WebSocket 进度等。
- 不要把模型执行、检索、prompt/schema、Agent 编排迁到 Java。

## 3. 当前数据与实现状态

已处理 5 本书：

| Book | Chapters | Entities | Relations | Events | Chunks |
|---|---:|---:|---:|---:|---:|
| 西游记 | 102 | 897 | 952 | 787 | 763 |
| 聊斋志异 | 25 | 510 | 241 | 262 | 471 |
| 搜神记 | 35 | 660 | 423 | 447 | 85 |
| 山海经 | 19 | 666 | 530 | 171 | 144 |
| 水浒传 | 126 | 1,024 | 1,055 | 846 | 912 |
| Total | 307 | 3,757 | 3,201 | 2,513 | 2,375 |

当前已有：

- Pipeline P1-P8：
  - import / split / chunk
  - extraction
  - ChapterFact build
  - entity governance
  - narrative build
  - Qdrant index
  - Neo4j graph projection
  - dataset export
- QA：
  - `QaRunner.answer()`
  - `RetrievalRunner.hybrid_search()`
  - lexical LIKE + Qdrant dense + ChapterFact + structured knowledge search
  - citations
  - multi-turn history by recent messages
- Quality：
  - entity name normalizer
  - relation deduper
  - event summarizer
- Eval：
  - 37 cases
  - weighted scoring
- UI：
  - browse/search/upload/pipeline/QA/training file download

近期修复：

- MySQL long request reconnect after LLM calls。
- Qdrant client API 改为 `query_points()`。
- 中文关键词抽取从固定 6 字非重叠改为滑动 n-gram。
- citation FK 中 `chapter_id=0` 改为 NULL。
- health endpoint 从固定 unavailable 改为真实 client checks。
- embedding preload 改成配置开关，避免本地模型未就绪时服务无法启动。

## 4. 当前技术约束

固定技术路线：

```text
Main backend now: Python FastAPI
Later product API: Java Spring Boot
DB: MySQL utf8mb4
Vector DB: Qdrant
Graph DB: Neo4j optional
Embedding: Qwen/Qwen3-Embedding-0.6B, 1024 dim, cosine
Local LLM: llama-server, local 9B
Cloud/API model: DeepSeek first
RAG: Evidence-first Hybrid RAG, not GraphRAG first
```

远程端口：

```text
MYSQL_PORT=13306
NEO4J_HTTP_PORT=17474
NEO4J_BOLT_PORT=17687
LLAMA_PORT=18080
RAG_AGENT_PORT=18081
QDRANT_PORT=16333
```

硬规则：

- 模型输出是 candidate data，不是真相。
- Evidence + review 决定是否接受。
- 不要全局应用 alias maps 到全文。实体视图必须 chapter-aware 或 stage-aware。
- 每个长任务必须写 `AgentRun` 和 `AgentStep`。
- 每次模型调用必须记录 `ModelCall`：prompt/revision/schema/provider/model/duration/errors/parse/evidence status。
- 每个答案必须有证据引用；没有证据时必须表达不足。

## 5. 现有文档应该参考什么

请优先参考：

```text
AGENTS.md
docs/00-product-goal.md
docs/01-architecture.md
docs/02-development-roadmap.md
docs/03-data-model.md
docs/04-agent-runtime.md
docs/05-pipeline.md
docs/06-rag-strategy.md
docs/07-quality-harness.md
docs/08-ai-reader-lessons.md
docs/09-deployment.md
docs/10-java-tech-stack.md
docs/qa-agent-design.md
docs/AI Reader/
```

`docs/qa-agent-design.md` 当前是“QA Agent”窄设计：think-act-observe + 5 个检索工具 + memory + context budget。它可以作为起点，但我们现在想把它升级为更通用的 `ReaderAgent`。

`docs/04-agent-runtime.md` 已经有两个 Agent 的雏形，但第二个还写成 QA Agent，范围不够。

## 6. AI Reader 参考材料中的关键经验

请结合这些本地材料：

```text
docs/AI Reader/AI Reader README.md
docs/AI Reader/AI Reader-1.pdf
docs/AI Reader/AI Reader-2.pdf
docs/AI Reader/AI Reader文章评论.md
```

我们从 AI Reader 里提炼到的重点：

1. 需求不清晰会导致系统松散。
   - 先 PRD / workflow / 验收标准，再让 Agent 执行。
   - 不要让 AI 在模糊目标下漫游。

2. LLM 只负责“看见”，不要负责全局真相。
   - 逐章提取 recall-oriented。
   - 跨章节一致性、别名归并、关系聚合、地理层级要用规则/算法/投票/审核层。

3. 别名合并是高风险核心。
   - 泛称、称谓、字号、短别名、复合人名会造成桥接污染。
   - Union-Find 需要安全边界。
   - 需要 blocklist / soft block / hard block / chapter-local evidence。

4. 长篇小说不能只靠摘要。
   - 伏笔往往是一两句不起眼的文本。
   - 摘要会丢掉弱信号。
   - 需要“候选线索池”和后续兑现/提醒链路，而不是只保留章节摘要。

5. ChapterFact 是合理中间层。
   - 每章先形成局部事实。
   - 全书知识图谱是聚合产物。
   - 不要 GraphRAG first。

6. 章节上下文很关键。
   - ContextSummaryBuilder / previous summaries / entity dictionaries 类似“读书笔记”。
   - 但要注意摘要不是 truth，只是上下文提示。

7. 关系是动态的。
   - 同一对人物可能“先敌后友”“同事+恋人”“表面冲突实际欣赏”。
   - 不应该只存一个最终主标签。
   - 应保留关系类型随章节/阶段变化。

8. 用户反馈要变成质量资产。
   - 错误 case 不应只改 prompt。
   - 应沉淀为 eval case、validator rule、blocklist、quality check、review task。

9. 创作辅助方向可行，但前提是分析质量扎实。
   - 分析出的世界观、人物关系、设定、伏笔链、描写模式可以反向作为 authoring input。
   - 但不要过早做“生成小说”，先做“读懂和整理小说”。

10. 领域思维比通用 GraphRAG 更重要。
   - 小说有体裁、叙事结构、视角、伏笔、设定演化、人物关系变化、作者遗忘/补丁。
   - 通用文档 RAG 不会自动理解这些。

## 7. 用户提出的新方向

用户明确希望：

> 设计两个 Agent：一个是当前的数据预处理 Agent，另一个是问答 Agent，但第二个不止于问答，还会有其他功能，如完善反哺知识库，伏笔、设定抽取，描述描写学习等等。可以参考 coding agent 的设计与它们实现的功能迁移到我们的 Agent 上。

用户额外提供的设计经验：

> 在 Agent 的 plan 阶段维护一个状态机能够极大降低幻觉，和长上下文带来的关键信息遗忘或颠倒错乱。这样做远比加更多 prompt 规则有效。通过 function call 约束 output 格式，可以把格式准确率从 95% 提升到 100%。

我们希望 GPT 特别评估：

- 是否应该把状态机作为 Agent runtime 的核心，而不是作为 prompt 规则。
- Planner 的输出是否必须是 function call / JSON schema / Pydantic model / GBNF constrained output。
- 状态机应该是“任务级状态”还是“每个 mode 各自状态”。
- 状态机如何和 `AgentRun` / `AgentStep` / `ModelCall` 对齐。
- 哪些状态由模型建议，哪些只能由代码迁移。

## 8. 初步建议：两个 Agent 的工作定义

这只是初步想法，欢迎 GPT 批判和重构。

### 8.1 PreprocessAgent

角色：离线知识构建器。

目标：把原文变成稳定、可审计、可检索、可修复、可反哺的知识资产。

输入：

- raw book text
- book metadata
- genre / author hints
- existing rules
- prior hints
- previous failed runs / review feedback

输出：

- chapters
- chunks
- mentions
- chapter_facts
- entity profiles
- relation facts
- event facts
- plot stages
- vector index
- graph projection
- eval/training dataset
- quality reports

可能状态机：

```text
NEW
-> SOURCE_DECODED
-> CHAPTERS_SPLIT
-> CHUNKS_BUILT
-> PRIOR_READY
-> MENTIONS_EXTRACTED
-> FACTS_BUILT
-> ENTITIES_GOVERNED
-> QUALITY_CHECKED
-> INDEXED
-> GRAPH_PROJECTED
-> DATASET_EXPORTED
-> DONE

Any state -> NEED_REVIEW / FAILED / CANCELED
```

关键原则：

- 每一步可恢复、可重试、可跳过已完成。
- LLM output 只能写 candidate。
- 每一步必须能解释用了什么 prompt/schema/model。
- 大任务必须有 AgentRun/AgentStep。
- 不让 LLM 直接做全局合并决策，合并必须经过规则/证据/审核。

### 8.2 ReaderAgent

角色：在线阅读、分析、知识反哺与创作辅助 Agent。

名字可以讨论。`QA Agent` 太窄，候选名：

- `ReaderAgent`
- `NarrativeAgent`
- `ReadingAgent`
- `AuthoringAnalysisAgent`
- `ResearchAgent`

目标：以 evidence-first 的方式回答、分析、追踪、补全，并把高价值发现转成可审核知识补丁。

输入：

- user query / task
- book_id / chapter scope / selected entity
- conversation history
- current reading position
- context memory
- existing knowledge graph

输出：

- cited answer
- analysis report
- trace result
- candidate knowledge patch
- follow-up question
- style card / trope card / setting card
- feedback signal for eval/quality

模式候选：

```text
answer        证据问答
analyze       人物/关系/事件/设定分析
trace         伏笔、物品、关系、设定演化追踪
enrich        反哺知识库，提出候选 patch
learn_style   描写、文风、叙事技法学习
compare       跨章节/跨人物/跨书比较
authoring     后续创作辅助，先不急
```

可能状态机：

```text
NEW_TASK
-> INTENT_CLASSIFIED
-> PLAN_READY
-> CONTEXT_LOADED
-> EVIDENCE_SEARCHING
-> EVIDENCE_COLLECTED
-> DRAFT_READY
-> VERIFIED
-> RESPONDED

Optional:
-> PATCH_PROPOSED
-> PATCH_PENDING_REVIEW
-> PATCH_ACCEPTED / PATCH_REJECTED

Any state -> NEED_FOLLOWUP / FAILED / CANCELED
```

关键原则：

- 所有事实性输出必须绑定 evidence。
- 记忆不能替代 evidence。
- Agent 可以提出知识库 patch，但不能直接改正式事实表。
- 反哺必须进入 review/quality pipeline。
- 长上下文由 context store 管理，不靠 prompt 硬塞。

## 9. 通用 Agent Runtime 初步设想

建议不要给两个 Agent 各写一套孤立 runtime，而是抽出公共组件：

```text
app/agent_runtime/
├── state_machine.py
├── planner.py
├── tool_registry.py
├── tool_executor.py
├── context_manager.py
├── memory_store.py
├── model_provider.py
├── model_call_store.py
├── run_store.py
├── schemas.py
└── trace.py
```

两个业务 Agent：

```text
app/preprocess_agent/
├── agent.py
├── states.py
├── tools/
└── prompts/

app/reader_agent/
├── agent.py
├── states.py
├── tools/
├── modes/
└── prompts/
```

希望 GPT 评估这个划分是否合理。也请评估是否保持 `app/qa/agent/`，还是改成 `app/reader_agent/`。

## 10. 记忆与上下文系统初步设想

我们想吸收 OpenViking 的思路，但短期不一定接入外部项目。

目标是做 NovelBridge 自己的 Context Store：

```text
L0: 100-200 token summary
L1: structured notes / bullet facts / state summary
L2: full evidence: chunk, chapter_fact, relation_fact, event_fact, citation
```

建议使用路径式 URI：

```text
nb://book/6
nb://book/6/chapter/12
nb://book/6/entity/孙悟空
nb://book/6/relation/孙悟空/唐僧
nb://book/6/thread/foreshadowing/金箍棒
nb://book/6/setting/取经任务
nb://book/6/style/appearance-description
```

检索流程可以是：

```text
intent classify
-> route to context namespace
-> load L0 summaries
-> choose relevant L1 nodes
-> retrieve L2 evidence only when needed
-> answer/analyze/patch with citations
```

请 GPT 帮忙评估：

- 哪些上下文应该存在 MySQL，哪些应该存在 Qdrant payload，哪些只做 runtime cache。
- 是否需要新增 `novel_context_node` / `novel_memory_node` / `novel_knowledge_patch` 表。
- 如何保存检索轨迹，方便调试。
- 会话结束后如何做 self-iteration，把有价值发现归档为 memory/patch/eval case。

## 11. 知识反哺机制初步设想

ReaderAgent 未来会发现现有知识库中的缺漏或错误，例如：

- 某角色别名遗漏。
- 某关系在某章节阶段发生变化。
- 某设定跨章节逐步揭示。
- 某伏笔在后文兑现。
- 某描写片段可以归入“人物外貌描写”“战斗描写”“环境氛围描写”样本库。

但它不能直接修改正式表。

建议流程：

```text
ReaderAgent discovers candidate
-> evidence collected
-> propose KnowledgePatch
-> validate schema
-> quality checks
-> optional model review / user review
-> accepted patches merge into formal stores
-> rejected patches become eval/guardrail examples if useful
```

希望 GPT 设计：

- `KnowledgePatch` schema。
- patch type：alias_add, relation_update, event_add, setting_update, foreshadowing_link, style_sample_add, citation_fix 等。
- review UI/API 的最小实现。
- patch 如何转成训练数据或 eval case。

## 12. 伏笔、设定、描写学习的概念模型

这些是后续重点能力，不要求一次实现，但需要设计时预留。

### 12.1 伏笔链

伏笔不是普通事件。它可能有状态：

```text
SEED        埋下
REMINDER    中间提醒
PAYOFF      兑现
ABANDONED   疑似未填坑
FALSE_LEAD  误导线索
UNKNOWN     不确定
```

需要追踪：

- clue text
- chapter_id
- involved entities
- setting/topic
- later payoff evidence
- confidence
- reader-visible vs author-intended uncertainty

请 GPT 设计 `foreshadowing_thread` 是否应该独立成表，还是先放入 ChapterFact JSON。

### 12.2 设定抽取与演化

设定可能不是一次性给出，而是逐步展开：

- 世界规则
- 修炼体系
- 阵营规则
- 物品规则
- 地理/空间规则
- 称号/身份体系
- 主角能力限制

状态可能是：

```text
INTRODUCED
PARTIALLY_EXPLAINED
CONFIRMED
CONTRADICTED
RETCONNED
OBSOLETE
```

### 12.3 描述描写学习

希望从文本中抽取可复用样本：

- 人物外貌描写
- 战斗描写
- 环境描写
- 情绪描写
- 群像调度
- 悬念设置
- 章节收尾 hook
- 伏笔提醒句
- 设定说明句

这类样本用于后续 authoring assistance，但必须保留原文出处和上下文，不能变成无来源的“风格记忆”。

## 13. 当前已知架构缺口

请 GPT 特别考虑这些现实缺口：

1. `docs/qa-agent-design.md` 中提到 `novel_chat_session.summary_text`，但当前 schema 没有该字段。
2. MySQL schema 有 `novel_model_call`，但 Python store 还缺完整 `ModelCallStore`。
3. `GraphQueryRunner` 目前没有完整 Neo4j 不可用 fallback。
4. QA Agent 设计当前只覆盖问答，不覆盖 trace/enrich/style/authoring。
5. 当前 `RetrievalRunner` 的 private helper 被 QA 复用，后续工具化时应抽出稳定 query services。
6. 当前 Java 已有一些业务聚合代码，但策略是不要继续扩 Java Agent 逻辑。
7. 当前 eval 只有 QA 37 cases，不足以评估伏笔、设定、关系演化、知识反哺。

## 14. 希望 GPT 输出的文档结构

请 GPT 最好输出以下结构：

1. Recommended Naming and Scope
   - 两个 Agent 应叫什么，职责边界是什么。

2. Architecture Overview
   - Runtime、PreprocessAgent、ReaderAgent、ContextStore、KnowledgePatch、Quality/Eval 的关系。

3. State Machines
   - 两个 Agent 的状态图。
   - 状态迁移条件。
   - 哪些迁移必须由代码判定。

4. Tool Design
   - Preprocess tools。
   - Reader tools。
   - Tool schema / function call / structured output 约束方式。

5. Memory / Context Store
   - L0/L1/L2 怎么落地到 MySQL/Qdrant。
   - URI/path namespace 怎么设计。
   - 检索轨迹怎么记录。

6. Knowledge Feedback Loop
   - KnowledgePatch schema。
   - Review / merge / reject 流程。
   - 如何防止污染正式知识库。

7. Data Model Changes
   - 必须新增的表。
   - 可以暂缓的表。
   - Qdrant collections。

8. Implementation Roadmap
   - 先做什么，不做什么。
   - 每个阶段的验收证据。

9. Risks and Guardrails
   - 别名污染、长上下文遗忘、伏笔漏检、过度自动反哺、Java/Python 边界漂移。

10. Open Questions
   - 需要用户或后续实验决定的问题。

## 15. 我们倾向的短期落地顺序

这是当前 Codex 的初步判断，GPT 可以推翻：

1. 先更新设计文档：`QA Agent` -> `ReaderAgent`。
2. 补公共 runtime 最小件：
   - state machine
   - tool schema
   - model call store
   - run/step trace helper
3. 用 runtime 包住现有 P1-P8，形成 `PreprocessAgent`，不重写 pipeline。
4. 做 ReaderAgent 的 `answer` mode，复用现有 retrieval/qa。
5. 做 ContextStore L0/L1/L2 的最小版本。
6. 做 `trace` mode：先支持关系演化 / 物品线索 / 简单设定追踪。
7. 做 `KnowledgePatch` 候选反哺，不直接 merge。
8. 再考虑伏笔链、描写学习、authoring assistance。

## 16. 最重要的判断

我们现在不需要一个“更复杂的 prompt”。我们需要：

- 显式状态机。
- 受约束的工具调用。
- 可追踪的运行记录。
- 可审计的证据链。
- 分层上下文加载。
- 候选知识补丁和审核机制。
- 可增长的 eval/quality harness。

如果 GPT 只能给一个核心建议，请围绕这个问题回答：

> NovelBridge 如何从现有 pipeline + QA 系统，演进为两个可控 Agent：一个负责离线知识构建，一个负责在线阅读/分析/反哺/创作辅助，同时避免 LLM 幻觉、长上下文遗忘、别名污染和知识库污染？

