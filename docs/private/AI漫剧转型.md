几个模型我都问了两轮，第一轮是你总结的这段话，第二轮是你能不能再搜集资料和深度思考，分析一下我这个agent如何实现和设计

deepseek:
你给出的转型方向非常清晰，而且抓住了 NovelBridge 最稀缺的差异化能力——**把长篇小说变成可追溯、可审计的结构化知识资产，再以此为基底输出 AI 漫剧生产包，而不是直接去卷视频生成**。这能让你避开“一键成片效果不可控、同质化严重”的红海，卡住上游“IP 结构化改编”的咽喉位置。

下面我按照架构师/技术顾问的角度，从**战略定位、架构拆解、七个约束落地、Stage 4 实施路线和风险提示**五个方面，把方案做实，方便你直接用于项目文档或开发排期。

---

## 1. 战略定位：为什么这个转向是对的

你现在的核心竞争力是 **“Evidence-first 的长篇小说理解 + 知识治理”**。普通阅读助手面对的问题是：  
- 用户需求分散，付费意愿低；  
- 伏笔回收、文风样本等能力很难量化验收；  
- 商业化路径模糊。

而 **AI 漫剧生产包** 直接面向 B 端制作团队，需求刚性：  
- 制作方急需“忠于原著的改编依据”，否则甲方不验收；  
- 当前视频生成工具缺的从来不是模型，而是**结构化的前期策划、一致性控制、多模型适配和证据链**；  
- 你能提供“可审计的改编包”，这是 ViMax、AIDrama Studio 等端到端工具做不到的事。

把 NovelBridge 定位为 **“长篇小说 IP → AI 漫剧制作包的证据化改编引擎”**，等于在“小说理解”和“视频生成”之间建立了一个高价值中间件层，商业化和验收都更容易讲清楚。

---

## 2. 架构如何适配：AdaptationAgent 与现有系统的关系

你已经有非常扎实的底座：`PreprocessAgent` 负责把小说变成结构化事实，`agent_runtime` 提供状态机、工具注册、证据校验和 trace 能力，`knowledge_patch` 负责可审核的修补。  
**AdaptationAgent 不应该另起炉灶，而应该作为 PreprocessAgent 的下游消费者，并在运行时复用相同的 Agent 框架。**

### 2.1 数据流
```text
原始小说 
→ PreprocessAgent（章节、chunk、ChapterFact、实体、关系、事件、叙事图）
→ AdaptationAgent（改编大纲、分集、资产卡、分镜、PromptPack、QC、导出）
→ 制作团队工作台（人工审核、锁定、调整）
→ 外部模型 API（仅作为可选出口，且为异步/标记阶段）
```

### 2.2 模式设计
`AdaptationAgent` 的每个 mode（plan_episodes、build_assets 等）都应实现为 Agent 的一个 **Action/Tool**，并注册到 `agent_runtime`。这样：  
- 每一步都有 `AgentRun/AgentStep` 记录；  
- 可以随时恢复、跳过已完成步骤；  
- LLM 调用都是 `ModelCall`，可审计；  
- 所有输出都带 `source_evidence` 引用。

AdaptationAgent 本身不直接修改正式知识库的事实表，它产出的资产卡、分镜卡、PromptPack 等都是 **候选制品（candidate artifacts）**，存放在新的 `adaptation_*` 表中，支持人工锁定和版本管理。  
只有当制作团队确认后，才可能通过 `knowledge_patch` 机制反向修正实体/关系/事件（例如发现原著某角色别名未识别）。

---

## 3. 七个约束的工程落地方式

你把容易被忽略的坑点列得很全，我直接给出对应的数据模型/流程设计建议：

| 约束                                | 实现方式                                                     |
| ----------------------------------- | ------------------------------------------------------------ |
| **1. 改编输出区分来源 + 绑定证据**  | 所有 `scene_card`, `shot_card`, `dialogue_line` 增加 `source_type` 枚举：`direct_adaptation`, `reasonable_compression`, `added_bridge`, `manual`, `model_completion`，并关联 `source_chapter_fact_ids` 或 `source_chunk_ids`。 |
| **2. 人工锁定，避免设置被洗**       | 每个核心制品（EpisodePlan, AssetCard, ShotCard）表加 `locked` 布尔字段和 `locked_fields` JSON。AdaptationAgent 在生成前必须先检查锁定字段，只允许追加/修订未锁定部分，且修订需生成 `diff` 记录。 |
| **3. 资产卡和 PromptPack 版本管理** | `asset_card` 加 `version` 和 `parent_id`，支持分叉。例如角色“少年版”“成年版”作为同一 entity 的不同 asset_version。`prompt_pack` 同理，与 asset 版本绑定。 |
| **4. PromptPack 结构化拆分**        | 定义 `PromptPack` 模型，字段如 `visual_subject`, `scene`, `character_refs (json)`, `action`, `emotion`, `camera`, `lighting`, `duration`, `dialogue`, `sound`, `negative_prompt`, `reference_binding`。`PromptAdapter` 为每个模型（Seedance 2.0, Wan/ComfyUI, Runway, Kling…）实现 `to_model_prompt(pack) -> dict`，不输出单一长字符串。 |
| **5. 镜头连续性状态**               | 新增 `ContinuityState` 表，记录 shot 之间的 `prev_shot_state`：`character_positions`, `prop_states`, `emotion_states`, `camera_direction`。QC 工具可通过对比相邻 shot 的状态差异来生成 `continuity_issue`。 |
| **6. 成本与风险评估**               | `shot_card` 增加 `estimated_generation_cost`, `difficulty_level`, `retry_risk`, `model_recommendation`, `manual_review_required`。可结合 prompt 复杂度、模型平均耗时来估算，辅助制作排期。 |
| **7. 版权与授权前置**               | `adaptation_project` 表包含 `source_license_status`, `adaptation_rights_note`, `external_ip_style_blocklist (json)`, `likeness_risk_flag`。在资产卡生成时，检查角色名/形象是否命中 IP 屏蔽列表，若高风险则标记并阻断生成相似风格参考。 |

这些约束必须从 MVP 第一版就埋好字段和接口，否则后期补成本极高。

---

## 4. Stage 4 MVP 实施路线图

你提出的 MVP 范围（3-5章 → 1集生产包）非常务实，我把它拆解成具体迭代：

### Phase 4A：合同 + 数据底座（1-2 周）
- 完成你列出的 4 份文档（16~19），明确数据模型、API 边界。
- 创建 MySQL 表：`adaptation_project`, `episode_plan`, `asset_card`, `scene_card`, `shot_card`, `prompt_pack`, `continuity_issue`。
- 实现基础 Python stores 和 Pydantic schemas。
- 复用现有的 book/chapter/chunk/evidence 查询接口。

### Phase 4B：AdaptationAgent 核心 modes（2-4 周）
按依赖顺序开发并注册为 Agent Actions：
1. `plan_episodes` → 基于章节范围，生成 EpisodePlan（大纲、章节选取理由、证据引用）。
2. `build_assets` → 从 ChapterFact 和实体/关系/事件中抽取角色、场景、道具资产卡，关联 entity_id。
3. `split_scenes` → 根据 episode plan 拆成 3-5 个 SceneCard。
4. `storyboard` → 每个场景生成 3-6 个 ShotCard，包含视觉描述、镜头、动作、对话片段。
5. `prompt_pack` → 为每个 ShotCard 生成结构化 PromptPack，并调用 `PromptAdapter` 输出至少 2 种模型格式样例。
6. `qc_continuity` → 检查相邻 shot 的角色、场景、道具一致性，生成 issue 列表。
7. `export` → 导出 Markdown/CSV/JSON 生产包。

所有 actions 必须遵循：只读取治理后的事实，LLM 输出通过规则校验后再入库，生成物均为候选态。

### Phase 4C：简单工作台 UI（2-3 周）
- 基于现有 FastAPI + 前端，增加：
  - 创建 adaptation project，选择章节范围。
  - 分集规划树形视图，支持拖拽调整、锁定大纲。
  - 资产卡画廊，显示角色/场景/道具卡片，支持人工修改、锁定、新建版本。
  - 分镜表视图（列表/看板），展示 ShotCard 缩略信息、PromptPack、证据来源。
  - 一键导出按钮。
  - QC 问题悬浮提示，可标记“已忽略”或“需修订”。
- 完全不需要视频预览，纯文本+结构化数据即可满足 MVP 需求。

### Phase 4D：接模型 API（可延后）
- 仅当制作团队需要即时看到视觉效果时才接 Seedance/Kling 等 API。
- 采用异步任务队列，生成视频/图片后关联回 ShotCard 的 `preview_url`。
- 这一阶段不影响核心生产包的架构。

---

## 5. 风险与坚守原则

1. **不要变成一个“视频包装器”**。你们的价值始终在 **生产包的可编辑性、可审计性和证据绑定**，视频只是可选的渲染结果。竞品都会生成视频，但极少能交出分镜卡上的原文出处和改编理由。
2. **AdaptationAgent 决不能绕过 PreprocessAgent 的事实治理**。必须强制所有资产卡、台词、场景描述都能回溯到 ChapterFact 或原文 chunk，否则就会重蹈“模型胡编、制作团队不信任”的覆辙。
3. **人工审核闭环比算法更重要**。锁定、版本比对、diff 查看、QC 问题流转这些功能看起来不 sexy，但它们是专业工具区别于玩具的核心。UI 要优先把审核效率做高。
4. **Prompt 适配器要允许制作团队自定义**。不要只内置一两种模型格式，要把 `prompt_pack` 的字段暴露给 UI，让导演/美术能微调关键词、镜头语言和负向提示词，再导出到不同模型。
5. **版权字段必须从一开始就严肃对待**，否则商业落地时会有致命风险。可以先只做记录和预警，但字段不能缺。

---

## 总结

你对 NovelBridge 的新定义——“**做长篇小说 IP 到 AI 漫剧生产包的证据化改编系统**”——方向完全正确，而且已经想清楚了和现有 PreprocessAgent、Evidence 体系、质量流程的衔接方式。接下来只要严格围绕 MVP 约束落地，把 AdaptionAgent 做成一个对制作团队真正可用的“前期策划+证据审查”工具，就足以建立起技术壁垒和行业口碑。

如果需要，我可以进一步帮你细化 `adaptation_project` 等表的 DDL、Pydantic schema 或 `AdaptationAgent` 某个 mode 的 prompt 模板和逻辑流程。

好的，这里重点聊聊 `AdaptationAgent` 如何在不毁掉 NovelBridge 现有“证据优先 + LLM 只负责提案、规则负责治理”这根脊梁的前提下，真正把小说理解资产转成能被漫剧制作团队直接使用的生产包。

---

### 1. 底层硬约束：LLM 只是“创意编剧”，治理系统才是“剧本医生”

*   **Mutation Engine (突变引擎)**：接收 LLM 输出的原始 JSON，解析成候选对象，并将其装入临时的 `candidate_state` 中，绝不直接修改正式表。同时标记 `source_evidence`：若 LLM 给出了 `source_chunk_ids` 或 `source_fact_ids`，引擎会标记为 `direct_adaptation`，否则标记为 `model_completion`。
*   **Validation Engine (校验引擎)**：对候选态运行所有约束规则。例如检查 `character_refs` 中的 `entity_id` 是否都在资产库里；检查前后 Shot 的角色位置、情绪状态是否断裂；检查 `estimated_generation_cost`、版权风险等字段。只有通过全部校验，才进入审核队列（Status: `pending_review`）。
*   **Arbitration Engine (仲裁引擎)**：当一个项目同时跑了多个 LLM 提议（如 V1.0 和 V1.1 版分集规划），仲裁引擎比较两者的 `evidence_score`、`continuity_issues` 等指标，或让人工从审核队列中选择采纳哪个版本。

这样，`AdaptationAgent` 产出的分集规划、资产卡、分镜卡就只是提案，必须经过完整的治理流水线，从根本上杜绝模型幻觉污染生产资产。

### 2. AdaptationAgent 的 7 个核心 Modes 设计

以下方案将尽可能减少对现有 Python 栈的侵入，复用 `agent_runtime`、`stores`、`clients` 等模块。

#### Mode 1: `plan_episodes` —— 把“章节取舍”变成可审计的决策链
**输入**：书籍 ID、目标集数 N、总时长 T
**流程**：
1.  **章节密度扫描**：通过 `stores` 获取每个 Chapter 下的 `ChapterFact` 和事件密度、实体密度，生成统计摘要。
2.  **关键情节提取**：LLM 根据密度热点，从叙事图（Neo4j）中检索关键 `Event` 节点及其因果关系链，形成候选“情节点（Plot Point）”。
3.  **分配与打包**：LLM 基于“每集应包含 1-2 个高潮 + 足够的起承转合”的规划模板，将情节点分配到各集。`EpisodePlan` 的 `source_chapter_ids` 字段会记录覆盖了哪些章节，`adaptation_note` 字段说明砍掉或合并了哪些次要线索及理由。
4.  **人工锁定与版本管理**：支持对一个 `EpisodePlan` 锁定部分字段（如“第 3 集必须涵盖 XX 事件”），锁定后重跑规划时 `Mutation Engine` 会检测并跳过。

#### Mode 2: `build_assets` —— 用知识图谱自动填充“角色/场景/道具卡”
**职责**：从治理后的实体、关系、事件数据中生成“制作规格书”，是 NovelBridge 最该发挥长板的地方。
*   **`asset_card` 表结构示例**：应包含 `entity_id`、`visual_traits`（让 LLM 基于小说描写和时代背景提案，但必须绑定证据）、`revision_history`（JSON 字段存储所有历史版本）以及 `locked_fields`（JSON，标记哪些字段已被人工锁定）。若有 `reference_image_url` 字段，还需增加 `likeness_risk_flag` 校验。

#### Mode 3: `split_scenes` —— 把一集拆成“可拍摄的场景”
Agent 读取锁定的 `EpisodePlan` 及其覆盖的 Chapter 原文和 `ChapterFact`，提取叙事节拍，并用 LLM 判断场景的自然起止点（如地点转换、时间跳跃、人物退场等），然后填入 `SceneCard`。其 `source_type` 字段需标记为 `direct_adaptation`（直接根据原文划分）或 `added_bridge`（新增的过渡情节）。最后，`SceneCard` 通过 `previous_scene_id` 和 `next_scene_id` 字段构建单向/双向链表，为后续连续性检查打好基础。

#### Mode 4: `storyboard` —— 让 LLM 用“导演思维”填 ShotCard
需要为每个 `SceneCard` 生成 3-6 个 `ShotCard`：
*   **核心字段**：除了 `shot_type`、`camera_movement`、`lighting`等，**重点设计 `continuity_state` (JSON 字段)**。
*   **连续性状态 (`continuity_state`)**：为跟踪镜头连续性，每个 ShotCard 在执行后都需要记录一个 `ContinuityState`（如 `character_positions`、`prop_states` 等）。这作为下一个 Shot 生成时的上下文，类似于 FilmWeaver 的 "shot memory" 机制。可通过 `Validation Engine` 比较相邻两个 Shot 的状态，检查位置、道具等是否断裂。

#### Mode 5: `prompt_pack` —— 结构化 Prompt 与多模型适配
为避免耦合，对每个 `ShotCard` 生成结构化的 `PromptPack` 对象（包含 `visual_subject`、`action`、`camera` 等抽象描述），且不包含任何模型特定语法。
之后，`PromptAdapter` 针对不同模型（Seedance、Wan、Kling 等）将 `PromptPack` 渲染为原生提示词。通过策略模式实现，每种模型一个 Adapter 类。

#### Mode 6: `qc_continuity` —— 自动化剧本监督
职责：自动检测生产包内、资产卡之间、分镜之间的各种不一致。
*   **资产一致性**：检查 `ShotCard` 中引用的角色（`character_refs`）与 `AssetCard` 中的视觉描述是否一致。
*   **情节一致性**：检查 `EpisodePlan` 与 `ShotCard` 的剧情逻辑是否闭环。
*   **连续性断裂**：基于 `ContinuityState` 自动检测镜头间的断裂。
*   **版权与伦理风险**：检查 `likeness_risk_flag`、`external_ip_style_blocklist` 等字段。

#### Mode 7: `export` —— 将一切打包为可执行的生产文件
职责：将审核通过并锁定后的制品，打包为 Markdown/CSV/JSON 等可直接分发或导入其他工具的生产包，而非直接调模型生成视频。`export` 会从 MySQL 中拉取数据并渲染导出格式。

### 3. 核心设计决策分析

#### 3.1 Agent 编排：用 LangGraph 做“导演”，确保流程严谨可控
对于你这种需要严格遵循“规划-执行-校验-审核”流水线的场景，**LangGraph** 是比 ReAct/Function Calling 和 AutoGPT 等自主循环模式更合适的选择。
*   **对比选择**：LangGraph 能精确控制执行图（Graph），每一步都可持久化为 Checkpoint，且每个节点都可追踪。而自主循环模式流程不透明，难以精确注入证据和强制校验。
*   **状态设计**：核心 `AdaptationGraphState` 是一个 Pydantic 模型，包含 `project`、`evidence`、`artifacts`、`human_locks` 和 `candidate`（Mutation Engine 产生的候选对象）等字段。
*   **条件边 (Conditional Edges)**：利用 LangGraph 条件边实现 `Validation Gate`，根据校验结果决定是进入人工审核、自动重试、分叉新版本还是直接跳转到下一步。

#### 3.2 共享运行时：`agent_runtime` 作为“片场”，统一管理所有 Agent
所有 Agent 都应注册到 `agent_runtime`，它作为“片场”统一管理一切。
*   **核心职责**：它管理 `AgentRun`/`AgentStep` 记录、`ToolCall`/`ModelCall` 记录、`ContextStore`（L0/L1/L2 上下文路由）、`Evidence/Citation` 校验和 `KnowledgePatch` 提案队列。它本身不应包含任何改编逻辑，只负责调度与记录。

### 4. 总结：为什么这套设计能落地

这套设计严格遵循“LLM 提案，系统治理”的核心原则，解决了将 AI 引入漫剧制作时“幻觉毁掉一致性”的核心痛点。两个 Agent 的分工和共享运行时将复用现有“证据优先”的资产，使 NovelBridge 成为真正可落地的严肃生产工具，而不仅是酷炫的 Demo。接下来的核心工作，是先将 `agent_runtime` 和 `Mutation/Validation Engine` 做出一个能跑通 `plan_episodes` 的 MVP。

gemini这是一个极其敏锐且极具商业价值的战略 Pivot。

将 NovelBridge 从“面向读者的阅读辅助工具”转向“面向 AI 漫剧/短剧制作团队的生产力基建”，完美规避了 B2C 阅读助手商业模式模糊、评价标准主观（如“文风像不像”、“伏笔找得全不全”）的死胡同。通过切入长篇小说与视频生成模型之间的“断层”，提供**结构化、可审计、带证据链的生产包（Production Package）**，直接击中了当前 AI 影视工业化最上游、最稀缺的痛点。

针对这个新方向，我完全赞同你的架构决策和边界划分。以下是对 Stage 4（Novel-to-AI-Drama Production Package MVP）的系统性梳理与演进建议，确保你的构想能在工程上稳步落地。

### 一、 核心架构与技术边界重申

保持克制是这个阶段成功的关键。现有的技术边界非常清晰，必须严格坚守：

- **语言与职责边界**：**Python-first** 依然是核心大脑。Agent runtime、RAG 检索、模型调用、质量控制和生产包生成全在 Python 层；**Java Spring Boot** 仅作为 Product API shell，负责业务级的任务状态调度、SSE/WebSocket 进度推送、前端接口聚合与权限管理。
- **数据来源底线**：**Evidence-first Hybrid RAG**。不迷信单纯的 GraphRAG，Neo4j 只是事实的投影。所有改编决策、场景拆分、角色提取，必须能追溯到 Qdrant 的 dense chunk 或结构化的 ChapterFact。
- **不越俎代庖**：系统是“导演助理”和“编剧”，而不是“放映机”。坚决不做“一键成片”，不直接对接视频生成 API，只输出标准化的数据交付物（JSON/CSV/Markdown）。

### 二、 Stage 4 落地路径：Novel-to-AI-Drama Production Package MVP

将目标限定在“输入 3-5 章，输出 1 集漫剧生产包”，是一个非常扎实的 MVP 范围。

#### 1. 核心 Schema 与数据模型建设

需要新增的底层数据表 / Pydantic Models 必须强结构化：

- `adaptation_project`：改编项目元数据（IP 授权、全局风格基调、全局黑名单）。
- `episode_plan`：分集大纲（包含本集对应的原文 Chapter/Chunk 范围、核心剧情 Beat）。
- `asset_card`：资产卡（角色、场景、核心道具），必须支持**版本控制**（V1.少年期, V2.黑化期）。
- `scene_card`：场次卡（时间、地点、出场人物、本场核心冲突）。
- `shot_card`：分镜卡（画面描述、景别、运镜、台词、旁白）。
- `prompt_pack`：结构化提示词包（后续通过 PromptAdapter 翻译给特定模型）。
- `continuity_issue`：连续性质检报告（记录逻辑断裂或穿帮风险）。

#### 2. AdaptationAgent 的核心流转 (Modes)

AdaptationAgent 的工作流是一个有向无环图（DAG），每个节点都必须支持**中断、人工 Review（Locking）与重试**：

1. **`plan_episodes`**：基于 PreprocessAgent 提取的 plot stages 和 event facts，圈定单集范围。
2. **`build_assets`**：聚合 entity profiles，生成可复用的 AssetCard。
3. **`split_scenes`**：将单集剧情拆解为连续的 SceneCard。
4. **`storyboard`**：为每个 Scene 生成具体的 ShotCard（包含台词重写与视觉描述）。
5. **`prompt_pack`**：将 ShotCard 转化为多维度的结构化 Prompt。
6. **`qc_continuity`**：扫描连续性，生成修复建议。
7. **`export`**：打包输出。

### 三、 工业化约束：7 大不可妥协的工程规则

为了让这个系统真正具备“生产工具”的属性，你在设计中提出的 7 个约束必须作为中间件或前置校验规则写入 `agent_runtime`：

- **证据链绑定 (Traceability)**：所有的改编产出字段（哪怕是一句新增的旁白），都必须有 `adaptation_type` 枚举（如 `direct_extract`, `compressed`, `model_inferred`, `manual_added`），并绑定 `source_citation`。
- **细粒度锁定 (Asset Locking)**：UI 层必须能回传 `is_locked=True` 状态。当用户锁定了某张 AssetCard 或某个 Shot 的运镜后，后续的 Agent Step（如重写或润色）在合并上下文时必须将其作为**不可变常量 (Immutable Fact)** 传入。
- **资产版本化 (Versioning)**：角色外貌和心态会随剧情演进。AssetCard 必须有 `timeline_anchor`（绑定到具体的事件节点或章节），确保在 ShotCard 检索角色资产时提取的是当前时间线的正确版本。
- **结构化 Prompt 库 (Structured Prompts)**：摒弃单句长文本。构建一套通用的 Schema：`{visual_subject, environment, action, emotion, camera_angle, lighting, style_refs, negative_prompt}`。通过 `PromptAdapter` 接口，针对 Seedance 2.0 拼接复杂的负面词，针对 ComfyUI 输出节点参数，针对 Kling 优化动作描述。
- **连续性状态机 (Continuity State)**：这是市面上工具最欠缺的。在生成第 $N$ 个 ShotCard 时，必须强行将第 $N-1$ 个 ShotCard 的 `prev_shot_state`（人物站位、情绪余波、手持道具状态）注入 Context。
- **工程指标评估 (Production Metrics)**：为每个 Shot 增加 `estimated_generation_cost`（算力预估）和 `difficulty_level`（模型生成难度，如“多人复杂交互”标为高危）。这能让导演快速决定哪些镜头可以妥协成静态特写。
- **合规与风控 (IP Compliance)**：在 `preprocess` 阶段或 `adapt_outline` 阶段，前置扫描 `external_ip_style_blocklist`（例如：禁止生成“漫威风格”、“特定明星脸”），防范侵权风险。

目前的思路已经非常透彻，不仅明确了做什么，更重要的是明确了**不做什么**。

为了推动 Stage 4 的实质性落地，在第一步（补充文档和合同）中，你希望我们先从哪一个核心 Schema（比如 `18-production-package-schema.md` 还是 `17-adaptation-agent-contract.md`）开始进行字段级的推演和设计？

这是一个极其敏锐且极具商业价值的战略 Pivot。

将 NovelBridge 从“面向读者的阅读辅助工具”转向“面向 AI 漫剧/短剧制作团队的生产力基建”，完美规避了 B2C 阅读助手商业模式模糊、评价标准主观（如“文风像不像”、“伏笔找得全不全”）的死胡同。通过切入长篇小说与视频生成模型之间的“断层”，提供**结构化、可审计、带证据链的生产包（Production Package）**，直接击中了当前 AI 影视工业化最上游、最稀缺的痛点。

针对这个新方向，我完全赞同你的架构决策和边界划分。以下是对 Stage 4（Novel-to-AI-Drama Production Package MVP）的系统性梳理与演进建议，确保你的构想能在工程上稳步落地。

### 一、 核心架构与技术边界重申

保持克制是这个阶段成功的关键。现有的技术边界非常清晰，必须严格坚守：

- **语言与职责边界**：**Python-first** 依然是核心大脑。Agent runtime、RAG 检索、模型调用、质量控制和生产包生成全在 Python 层；**Java Spring Boot** 仅作为 Product API shell，负责业务级的任务状态调度、SSE/WebSocket 进度推送、前端接口聚合与权限管理。
- **数据来源底线**：**Evidence-first Hybrid RAG**。不迷信单纯的 GraphRAG，Neo4j 只是事实的投影。所有改编决策、场景拆分、角色提取，必须能追溯到 Qdrant 的 dense chunk 或结构化的 ChapterFact。
- **不越俎代庖**：系统是“导演助理”和“编剧”，而不是“放映机”。坚决不做“一键成片”，不直接对接视频生成 API，只输出标准化的数据交付物（JSON/CSV/Markdown）。

### 二、 Stage 4 落地路径：Novel-to-AI-Drama Production Package MVP

将目标限定在“输入 3-5 章，输出 1 集漫剧生产包”，是一个非常扎实的 MVP 范围。

#### 1. 核心 Schema 与数据模型建设

需要新增的底层数据表 / Pydantic Models 必须强结构化：

- `adaptation_project`：改编项目元数据（IP 授权、全局风格基调、全局黑名单）。
- `episode_plan`：分集大纲（包含本集对应的原文 Chapter/Chunk 范围、核心剧情 Beat）。
- `asset_card`：资产卡（角色、场景、核心道具），必须支持**版本控制**（V1.少年期, V2.黑化期）。
- `scene_card`：场次卡（时间、地点、出场人物、本场核心冲突）。
- `shot_card`：分镜卡（画面描述、景别、运镜、台词、旁白）。
- `prompt_pack`：结构化提示词包（后续通过 PromptAdapter 翻译给特定模型）。
- `continuity_issue`：连续性质检报告（记录逻辑断裂或穿帮风险）。

#### 2. AdaptationAgent 的核心流转 (Modes)

AdaptationAgent 的工作流是一个有向无环图（DAG），每个节点都必须支持**中断、人工 Review（Locking）与重试**：

1. **`plan_episodes`**：基于 PreprocessAgent 提取的 plot stages 和 event facts，圈定单集范围。
2. **`build_assets`**：聚合 entity profiles，生成可复用的 AssetCard。
3. **`split_scenes`**：将单集剧情拆解为连续的 SceneCard。
4. **`storyboard`**：为每个 Scene 生成具体的 ShotCard（包含台词重写与视觉描述）。
5. **`prompt_pack`**：将 ShotCard 转化为多维度的结构化 Prompt。
6. **`qc_continuity`**：扫描连续性，生成修复建议。
7. **`export`**：打包输出。

### 三、 工业化约束：7 大不可妥协的工程规则

为了让这个系统真正具备“生产工具”的属性，你在设计中提出的 7 个约束必须作为中间件或前置校验规则写入 `agent_runtime`：

- **证据链绑定 (Traceability)**：所有的改编产出字段（哪怕是一句新增的旁白），都必须有 `adaptation_type` 枚举（如 `direct_extract`, `compressed`, `model_inferred`, `manual_added`），并绑定 `source_citation`。
- **细粒度锁定 (Asset Locking)**：UI 层必须能回传 `is_locked=True` 状态。当用户锁定了某张 AssetCard 或某个 Shot 的运镜后，后续的 Agent Step（如重写或润色）在合并上下文时必须将其作为**不可变常量 (Immutable Fact)** 传入。
- **资产版本化 (Versioning)**：角色外貌和心态会随剧情演进。AssetCard 必须有 `timeline_anchor`（绑定到具体的事件节点或章节），确保在 ShotCard 检索角色资产时提取的是当前时间线的正确版本。
- **结构化 Prompt 库 (Structured Prompts)**：摒弃单句长文本。构建一套通用的 Schema：`{visual_subject, environment, action, emotion, camera_angle, lighting, style_refs, negative_prompt}`。通过 `PromptAdapter` 接口，针对 Seedance 2.0 拼接复杂的负面词，针对 ComfyUI 输出节点参数，针对 Kling 优化动作描述。
- **连续性状态机 (Continuity State)**：这是市面上工具最欠缺的。在生成第 $N$ 个 ShotCard 时，必须强行将第 $N-1$ 个 ShotCard 的 `prev_shot_state`（人物站位、情绪余波、手持道具状态）注入 Context。
- **工程指标评估 (Production Metrics)**：为每个 Shot 增加 `estimated_generation_cost`（算力预估）和 `difficulty_level`（模型生成难度，如“多人复杂交互”标为高危）。这能让导演快速决定哪些镜头可以妥协成静态特写。
- **合规与风控 (IP Compliance)**：在 `preprocess` 阶段或 `adapt_outline` 阶段，前置扫描 `external_ip_style_blocklist`（例如：禁止生成“漫威风格”、“特定明星脸”），防范侵权风险。

目前的思路已经非常透彻，不仅明确了做什么，更重要的是明确了**不做什么**。

为了推动 Stage 4 的实质性落地，在第一步（补充文档和合同）中，你希望我们先从哪一个核心 Schema（比如 `18-production-package-schema.md` 还是 `17-adaptation-agent-contract.md`）开始进行字段级的推演和设计？

千问

NovelBridge 从通用小说阅读分析转向 **AI 漫剧/短剧生产包证据化改编系统** 的战略方向是**合理且具备市场差异化优势的**。其核心价值在于将已验证的“结构化小说理解能力”精准对接当前漫剧行业最迫切的 **“证据化生产资料缺失”痛点**，而非重复“一键成片”的低效竞争。以下结合行业现状与技术可行性展开分析：

------

## 一、战略转型的合理性与市场依据

### 1. **行业痛点精准匹配**

- 当前漫剧行业的核心矛盾是 **“量的狂欢”与“质的贫瘠”并存**：2025年AI漫剧市场规模已达168亿元（占微短剧15%-17%），但 **40%-50%的返工工作量集中在角色穿帮、场景断裂等低级错误修正**，根源在于缺乏基于原著证据链的结构化生产包。
- NovelBridge 的 **ChapterFact + Evidence 绑定机制** 可直接解决该问题：通过强制要求所有改编输出（如角色卡、分镜卡）关联原文证据，避免当前行业普遍依赖“抽卡式返工”的低效模式。

### 2. **差异化竞争壁垒**

- 市面工具（如LumenX、Jellyfish）聚焦 **“生成结果”**，而 NovelBridge 的 **证据化改编层** 填补了上游关键空白：
	- 现有工具无法追溯“角色设定是否偏离原著”，NovelBridge 可通过 `source_evidence` 字段绑定原文段落，**人工审核时一键定位冲突**。
	- 行业80%的穿帮问题源于 **镜头间状态断裂**（如角色位置突变），NovelBridge 的 `prev_shot_state` 连续性校验机制（要求记录 `character_position/prop_state/emotion_state`）能系统性规避此类风险。

------

## 二、关键实施建议：强化证据化核心能力

### 1. **必须坚守的证据化原则**

- **所有改编输出需标注来源类型**：  
	- **原文直接改编**（必须绑定 `ChapterFact` 或原文段落ID）  
	- **合理压缩**（需说明删减逻辑，保留核心证据链）  
	- **新增桥段**（强制要求人工标注 `manual_addition` 并关联创作意图）  
	- **模型补全**（仅限非关键细节，且需标记 `model_completion` 风险等级）
		*此举可规避版权争议，并为后续人工审核提供明确路径。*
- **禁止直接输出最终视频**：MVP 阶段应 **仅交付结构化生产包**（如ShotCard JSON + PromptPack + 证据快照），避免因生成质量波动削弱证据可信度。

### 2. **需优先落地的技术特性**

- **动态锁定机制**：
	允许制作团队对 **角色资产卡、分集大纲** 等关键节点设置 `manual_lock` 标志，后续重生成时 **自动跳过已锁定项**，解决行业普遍存在的“设定漂移”问题。
- **多模型Prompt结构化拆解**：
	PromptPack 必须拆分为 **标准化字段**（如 `visual_subject`、`camera_motion`、`lighting_hint`），而非单字符串。例如：  
	- `character_refs` 字段应关联 NovelBridge 的 **实体ID**（非名称），确保跨镜头一致性  
	- `negative_prompt` 需自动注入原著 **禁忌元素**（如角色无左撇子设定，则强制添加 `left-handed`）
		*此设计可适配Seedance 2.0等工具的语义理解需求，避免提示词失效。*
- **连续性风险预检系统**：
	在 `qc_continuity` 环节，需基于 `prev_shot_state` 与当前ShotCard的 **状态差异值** 输出风险评分。例如：  
	- 角色位置偏移 >15% → **高风险**（需人工复核）  
	- 道具状态冲突 → **阻断级错误**（自动暂停导出）

------

## 三、需规避的常见陷阱

### 1. **版权合规前置化**

- 在 `adaptation_project` 表中必须包含：  
	- `source_license_status`（原著授权状态）  
	- `likeness_risk_flag`（肖像权风险，如角色高度还原真人）  
	- `external_ip_style_blocklist`（禁用风格，避免侵权争议）
		*当前司法实践已明确：AI生成内容若包含未经授权的IP元素（如奥特曼案），平台需承担主动审查责任。*

### 2. **拒绝“过度自动化”**

- **关键决策必须人工介入**：  
	- 实体合并/拆分（`entity_merge/split`）  
	- 新增桥段超过剧情权重10%  
	- 涉及敏感设定修改（如角色人种、性别）
- **所有知识补丁需走审核流程**：`knowledge_patch` 层应记录 `proposed_by`（AI/人工）、`evidence_strength`、`review_status`，**禁止绕过质量流程直接写入主库**。

------

## 结论

NovelBridge 转向 **AI漫剧生产包证据化系统** 的核心优势在于：**将小说结构化理解能力转化为可审计、可追溯的工业化生产资料**，直接解决行业40%-50%返工率的痛点。实施中必须 **严守证据绑定原则**，优先落地动态锁定、结构化Prompt、连续性预检三大特性，并将版权合规嵌入生产包生成流程。当前阶段应聚焦 **交付制作团队可直接使用的结构化数据包**（而非生成视频），以此建立与“一键成片”工具的**本质差异**——前者提供 **可控的生产确定性**，后者仅提供 **随机的生成结果**。

NovelBridge 从通用小说阅读分析转向 **AI 漫剧/短剧生产包证据化改编系统** 的战略方向是**合理且具备市场差异化优势的**。其核心价值在于将已验证的“结构化小说理解能力”精准对接当前漫剧行业最迫切的 **“证据化生产资料缺失”痛点**，而非重复“一键成片”的低效竞争。以下结合行业现状与技术可行性展开分析：

------

## 一、战略转型的合理性与市场依据

### 1. **行业痛点精准匹配**

- 当前漫剧行业的核心矛盾是 **“量的狂欢”与“质的贫瘠”并存**：2025年AI漫剧市场规模已达168亿元（占微短剧15%-17%），但 **40%-50%的返工工作量集中在角色穿帮、场景断裂等低级错误修正**，根源在于缺乏基于原著证据链的结构化生产包。
- NovelBridge 的 **ChapterFact + Evidence 绑定机制** 可直接解决该问题：通过强制要求所有改编输出（如角色卡、分镜卡）关联原文证据，避免当前行业普遍依赖“抽卡式返工”的低效模式。

### 2. **差异化竞争壁垒**

- 市面工具（如LumenX、Jellyfish）聚焦 **“生成结果”**，而 NovelBridge 的 **证据化改编层** 填补了上游关键空白：
	- 现有工具无法追溯“角色设定是否偏离原著”，NovelBridge 可通过 `source_evidence` 字段绑定原文段落，**人工审核时一键定位冲突**。
	- 行业80%的穿帮问题源于 **镜头间状态断裂**（如角色位置突变），NovelBridge 的 `prev_shot_state` 连续性校验机制（要求记录 `character_position/prop_state/emotion_state`）能系统性规避此类风险。

------

## 二、关键实施建议：强化证据化核心能力

### 1. **必须坚守的证据化原则**

- **所有改编输出需标注来源类型**：  
	- **原文直接改编**（必须绑定 `ChapterFact` 或原文段落ID）  
	- **合理压缩**（需说明删减逻辑，保留核心证据链）  
	- **新增桥段**（强制要求人工标注 `manual_addition` 并关联创作意图）  
	- **模型补全**（仅限非关键细节，且需标记 `model_completion` 风险等级）
		*此举可规避版权争议，并为后续人工审核提供明确路径。*
- **禁止直接输出最终视频**：MVP 阶段应 **仅交付结构化生产包**（如ShotCard JSON + PromptPack + 证据快照），避免因生成质量波动削弱证据可信度。

### 2. **需优先落地的技术特性**

- **动态锁定机制**：
	允许制作团队对 **角色资产卡、分集大纲** 等关键节点设置 `manual_lock` 标志，后续重生成时 **自动跳过已锁定项**，解决行业普遍存在的“设定漂移”问题。
- **多模型Prompt结构化拆解**：
	PromptPack 必须拆分为 **标准化字段**（如 `visual_subject`、`camera_motion`、`lighting_hint`），而非单字符串。例如：  
	- `character_refs` 字段应关联 NovelBridge 的 **实体ID**（非名称），确保跨镜头一致性  
	- `negative_prompt` 需自动注入原著 **禁忌元素**（如角色无左撇子设定，则强制添加 `left-handed`）
		*此设计可适配Seedance 2.0等工具的语义理解需求，避免提示词失效。*
- **连续性风险预检系统**：
	在 `qc_continuity` 环节，需基于 `prev_shot_state` 与当前ShotCard的 **状态差异值** 输出风险评分。例如：  
	- 角色位置偏移 >15% → **高风险**（需人工复核）  
	- 道具状态冲突 → **阻断级错误**（自动暂停导出）

------

## 三、需规避的常见陷阱

### 1. **版权合规前置化**

- 在 `adaptation_project` 表中必须包含：  
	- `source_license_status`（原著授权状态）  
	- `likeness_risk_flag`（肖像权风险，如角色高度还原真人）  
	- `external_ip_style_blocklist`（禁用风格，避免侵权争议）
		*当前司法实践已明确：AI生成内容若包含未经授权的IP元素（如奥特曼案），平台需承担主动审查责任。*

### 2. **拒绝“过度自动化”**

- **关键决策必须人工介入**：  
	- 实体合并/拆分（`entity_merge/split`）  
	- 新增桥段超过剧情权重10%  
	- 涉及敏感设定修改（如角色人种、性别）
- **所有知识补丁需走审核流程**：`knowledge_patch` 层应记录 `proposed_by`（AI/人工）、`evidence_strength`、`review_status`，**禁止绕过质量流程直接写入主库**。

------

## 结论

NovelBridge 转向 **AI漫剧生产包证据化系统** 的核心优势在于：**将小说结构化理解能力转化为可审计、可追溯的工业化生产资料**，直接解决行业40%-50%返工率的痛点。实施中必须 **严守证据绑定原则**，优先落地动态锁定、结构化Prompt、连续性预检三大特性，并将版权合规嵌入生产包生成流程。当前阶段应聚焦 **交付制作团队可直接使用的结构化数据包**（而非生成视频），以此建立与“一键成片”工具的**本质差异**——前者提供 **可控的生产确定性**，后者仅提供 **随机的生成结果**。

kimi
我已完整阅读了这份 NovelBridge 项目文档。以下是我的结构化总结与关键观察：

---

## 一、项目定位总结

**一句话定位**：NovelBridge 不是普通的小说阅读助手，也不是一键成片工具，而是**"长篇小说 IP → 结构化知识资产 → AI 漫剧生产包"的证据化改编系统**。

核心差异化在于：
- **上游稀缺层**：做其他工具（LumenX、Jellyfish、BigBanana）不愿做或做不好的"长篇小说深度理解 + 改编决策 + 证据追溯"
- **证据化原则**：所有改编输出必须绑定原文证据，区分"原文改编/压缩/新增/人工/模型补全"
- **生产包导向**：输出的是结构化生产资料（分集规划、资产卡、分镜卡、PromptPack），而非直接生成视频

---

## 二、当前架构（Stage 3）速览

| 层级         | 模块                   | 职责                                                         |
| ------------ | ---------------------- | ------------------------------------------------------------ |
| **接口层**   | `api/`                 | HTTP API（books、qa、pipeline、eval 等）                     |
| **流程层**   | `pipeline/`            | P1-P8 预处理主链路（导入→切章→切块→抽取→治理→索引→图投影→导出） |
| **问答层**   | `qa/`                  | Hybrid RAG（lexical + dense + ChapterFact + structured lookup） |
| **质量层**   | `quality/`             | 实体名归一、关系去重、事件总结                               |
| **评测层**   | `eval/`                | 37 个 case + 加权评分                                        |
| **Agent 层** | `agent_runtime/`       | 状态机、Action/Tool 注册、Evidence 校验、运行记录            |
| **数据层**   | MySQL + Qdrant + Neo4j | MySQL 为主事实库，Qdrant 向量检索，Neo4j 仅做验证后图投影    |

**双 Agent 架构**：
- `PreprocessAgent`：离线知识构建，编排 P1-P8，状态机驱动，可恢复
- `ReaderAgent`：在线问答分析，证据优先，记忆不能替代证据

---

## 三、Stage 4 新方向：AI 漫剧生产包 MVP

### 3.1 核心 Agent 调整
保留 `PreprocessAgent`（原著理解），**新增/升级 `AdaptationAgent`**（漫剧导演 Agent）

### 3.2 AdaptationAgent 职责
| Mode             | 输出                     |
| ---------------- | ------------------------ |
| `adapt_outline`  | 改编策略                 |
| `plan_episodes`  | 分集规划、章节取舍       |
| `build_assets`   | 角色/场景/道具 AssetCard |
| `split_scenes`   | 场次拆分 SceneCard       |
| `storyboard`     | 分镜 ShotCard            |
| `rewrite_script` | 台词/旁白                |
| `prompt_pack`    | 多模型结构化提示词包     |
| `qc_continuity`  | 连续性质检报告           |
| `export`         | Markdown/CSV/JSON 生产包 |

### 3.3 MVP 范围
- **输入**：1 本书的 3-5 章
- **输出**：1 集 AI 漫剧生产包
  - 1 个 EpisodePlan
  - 3-5 个 SceneCard
  - 12-24 个 ShotCard
  - 主要 AssetCard
  - PromptPack
  - 旁白/台词
  - QC Report
  - 导出文件

---

## 四、文档中明确的关键约束（高价值设计决策）

| 约束                  | 说明                                                         |
| --------------------- | ------------------------------------------------------------ |
| **证据绑定**          | 所有改编输出区分来源类型，尽量绑定 source evidence           |
| **人工锁定**          | 支持锁定角色资产、场景风格、分集大纲、ShotCard，防止重生洗掉设定 |
| **版本管理**          | AssetCard / PromptPack 需版本管理（不同年龄段、服装、形态、表情、参考图） |
| **PromptPack 结构化** | 不写成单个字符串，拆为 `visual_subject`、`scene`、`character_refs`、`action`、`emotion`、`camera`、`lighting`、`duration`、`dialogue`、`sound`、`negative_prompt`、`reference_binding` 等字段 |
| **PromptAdapter**     | 将结构化 PromptPack 适配 Seedance 2.0、Wan/ComfyUI、Runway、Veo、Kling、Hailuo 等不同模型 |
| **镜头连续性状态**    | 记录 `prev_shot_state`、`character_position`、`prop_state`、`emotion_state`、`camera_direction`，防止镜头断裂 |
| **生成成本估算**      | 记录 `estimated_generation_cost`、`difficulty_level`、`retry_risk`、`model_recommendation`、`manual_review_required` |
| **版权合规前置**      | `source_license_status`、`adaptation_rights_note`、`external_ip_style_blocklist`、`likeness_risk_flag` |

---

## 五、建议补充的潜在风险点

虽然文档非常详尽，但以下方面建议 Stage 4 文档中进一步明确：

1. **长上下文处理**：3-5 章的小说原文 + 已有知识库（307 章/3757 实体）输入到 AdaptationAgent 时，如何控制上下文窗口？是否需要章节级摘要而非全量原文？
2. **AssetCard 与原著 Entity Profile 的映射**：`PreprocessAgent` 治理后的实体如何自动映射为 `AdaptationAgent` 的视觉资产？是否需要人工审核中间态？
3. **ShotCard 的时空一致性校验机制**：`qc_continuity` 是规则驱动还是模型驱动？跨 Scene 的连续性如何追溯？
4. **PromptPack 的 A/B 测试与效果回传**：生成生产包后，如果制作团队发现某 Prompt 在 Seedance 2.0 上效果差，如何反馈到系统优化？
5. **与 Java Spring Boot 的边界**：Stage 4 的 UI 工作台（分集规划、资产卡、分镜表）是否由 Java 层负责？Python 层只暴露 API？

---

## 六、下一步您可以让我做什么？

请告诉我您希望我针对这份文档提供哪类帮助：

- **A. 评审 Stage 4 架构设计**：指出潜在漏洞、补充边界情况、优化模块拆分
- **B. 生成 Stage 4 核心文档草稿**：如 `16-ai-drama-direction.md`、`17-adaptation-agent-contract.md`、`18-production-package-schema.md` 等
- **C. 设计数据库 Schema**：`adaptation_project`、`episode_plan`、`asset_card`、`scene_card`、`shot_card`、`prompt_pack`、`continuity_issue` 的表结构
- **D. 绘制系统架构图**：Stage 4 的 Agent 交互、数据流、模块依赖图
- **E. 编写 AdaptationAgent 核心代码骨架**：如 `AdaptationAgent` 类、`plan_episodes`、`storyboard`、`prompt_pack` 等 mode 的 Python 接口
- **F. 对比分析**：与 LumenX / Jellyfish / BigBanana 的差异化竞争力分析
- **G. 其他**：请直接说明您的需求



我来为你进行更深入的资料搜集和架构思考，这次聚焦于**具体实现细节**、**代码级设计**和**与现有 NovelBridge 的无缝集成**。
基于最新搜集的学术文献、工业实践和前沿论文，我为你提供一份**可落地的代码级深度设计分析**。这次聚焦在**具体实现机制**、**Prompt 工程模板**、**状态机 Checkpoint 设计**和**与现有 NovelBridge 的无缝集成**上。

---

## 一、核心新发现（直接影响设计决策）

### 1.1 角色一致性：I2I Seed Frame 是"最关键组件"

根据论文 *Lights, Camera, Consistency: A Multistage Pipeline for Character-Stable AI Video Stories* 的消融实验：

| 配置                                            | 角色一致性评分 |
| ----------------------------------------------- | -------------- |
| 完整管道（含 Character Image + I2I Seed Frame） | **7.99**       |
| 去掉 Character Image（仅文本描述）              | 5.78           |
| 去掉 I2I Seed Frame（纯 T2V）                   | **0.55**       |

**关键洞察**：没有 I2I（Image-to-Image）种子帧作为视觉锚点，即使给视频模型角色图像，一致性也会灾难性崩溃。这意味着 NovelBridge 的 `AssetCard` 不能只存文本描述，**必须生成并缓存角色的"标准肖像"和"多角度转身图"**，作为每个 Shot 的 I2I 输入。

### 1.2 结构化输出的现实约束

根据 *PARSE: LLM Driven Schema Optimization* 和 *DeepJSONEval* 的研究：
- GPT-4 在复杂提取任务中仍有 **11.97% 的无效响应率**
- 即使使用约束解码（如 vLLM 的 XGrammar/Guidance），复杂嵌套 JSON 的生成仍是挑战
- **"Thought of Structure" 范式**（先进行结构推理再生成）可提升 44.89%

这意味着 `AdaptationAgent` 的 LLM 调用不能是"一次生成完整 EpisodePlan"，而应该是**分阶段生成 + 增量验证**。

### 1.3 多 Agent 状态机的工业最佳实践

根据 Microsoft Azure 架构中心 和 LangGraph/LlamaIndex 社区实践：
- **必须显式状态机**：不要让 LLM 通过上下文"记住"执行到哪一步
- **Checkpoint 外部持久化**：每个阶段边界序列化状态到 Redis/Postgres
- **验证 Agent 输出后再传递**：低置信度、格式错误或离题的响应会级联污染下游
- **Circuit Breaker**：对模型服务做熔断，避免级联故障

---

## 二、AdaptationAgent 代码级架构设计

### 2.1 状态机核心设计（不再依赖 LLM 记忆）

```python
# apps/rag-agent/app/adaptation_agent/state_machine.py

from enum import Enum, auto
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import json

class AdaptationStage(Enum):
    """改编流程的显式阶段，每个阶段对应一个可恢复的检查点"""
    INIT = auto()
    PLAN_EPISODES = auto()      # 分集规划
    BUILD_ASSETS = auto()       # 资产卡构建
    SPLIT_SCENES = auto()       # 场次拆分
    STORYBOARD = auto()         # 分镜生成
    REWRITE_SCRIPT = auto()     # 台词/旁白
    GENERATE_PROMPTS = auto()   # PromptPack 生成
    QC_CONTINUITY = auto()      # 连续性质检
    HUMAN_REVIEW = auto()       # 人工审核（如触发）
    EXPORT = auto()             # 导出生产包
    COMPLETED = auto()
    FAILED = auto()

class StageState(BaseModel):
    """每个阶段的状态快照"""
    stage: AdaptationStage
    status: str  # "pending" | "running" | "completed" | "failed" | "skipped"
    input_data: Dict[str, Any]      # 进入此阶段时的输入
    output_data: Dict[str, Any]     # 此阶段产生的输出（序列化后的对象ID）
    evidence_bindings: List[str]    # 证据绑定列表
    error_info: Optional[str] = None
    retry_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class AdaptationState(BaseModel):
    """完整的改编状态，可序列化到 MySQL/Redis"""
    run_id: str
    project_id: str
    current_stage: AdaptationStage
    completed_stages: List[AdaptationStage]
    stage_states: Dict[str, StageState]  # stage.name -> StageState
    locked_entities: Dict[str, Any]    # 人工锁定的内容
    global_context: Dict[str, Any]      # 跨阶段共享上下文
    version: int = 1
    
    def to_checkpoint(self) -> str:
        """序列化为 JSON 字符串存储"""
        return self.model_dump_json()
    
    @classmethod
    def from_checkpoint(cls, json_str: str) -> "AdaptationState":
        """从检查点恢复"""
        return cls.model_validate_json(json_str)
```

### 2.2 Agent 主循环（Supervisor + Pipeline 组合）

```python
# apps/rag-agent/app/adaptation_agent/agent.py

class AdaptationAgent:
    def __init__(self, runtime: AgentRuntime, state_store: StateStore):
        self.runtime = runtime
        self.state_store = state_store
        self.modes = {
            AdaptationStage.PLAN_EPISODES: PlanEpisodesMode(),
            AdaptationStage.BUILD_ASSETS: BuildAssetsMode(),
            AdaptationStage.SPLIT_SCENES: SplitScenesMode(),
            AdaptationStage.STORYBOARD: StoryboardMode(),
            AdaptationStage.REWRITE_SCRIPT: RewriteScriptMode(),
            AdaptationStage.GENERATE_PROMPTS: GeneratePromptsMode(),
            AdaptationStage.QC_CONTINUITY: QCContinuityMode(),
            AdaptationStage.EXPORT: ExportMode(),
        }
    
    async def run(self, project_id: str, resume_from: Optional[str] = None) -> AdaptationResult:
        """主执行循环，支持从检查点恢复"""
        
        # 1. 加载或初始化状态
        if resume_from:
            state = await self.state_store.load(resume_from)
            logger.info(f"Resuming adaptation from stage: {state.current_stage}")
        else:
            state = AdaptationState(
                run_id=generate_uuid(),
                project_id=project_id,
                current_stage=AdaptationStage.INIT,
                completed_stages=[],
                stage_states={},
                locked_entities=await self.load_locked_entities(project_id),
                global_context=await self.load_project_context(project_id)
            )
        
        # 2. 状态机主循环
        while state.current_stage not in [AdaptationStage.COMPLETED, AdaptationStage.FAILED]:
            stage = state.current_stage
            mode = self.modes.get(stage)
            
            if not mode:
                raise ValueError(f"No mode registered for stage: {stage}")
            
            # 2.1 检查是否可跳过（已完成且未变更输入）
            if self._can_skip_stage(state, stage):
                state.completed_stages.append(stage)
                state.current_stage = self._next_stage(stage)
                await self._save_checkpoint(state)
                continue
            
            # 2.2 执行阶段（带重试和熔断）
            try:
                stage_state = StageState(
                    stage=stage,
                    status="running",
                    input_data=self._prepare_stage_input(state, stage),
                    started_at=datetime.utcnow()
                )
                state.stage_states[stage.name] = stage_state
                
                # 执行核心逻辑
                result = await self._execute_with_circuit_breaker(
                    mode, 
                    stage_state.input_data, 
                    state.global_context
                )
                
                # 2.3 质量门：验证输出
                validation = await self._quality_gate(stage, result)
                if not validation.passed:
                    if validation.retryable and stage_state.retry_count < 3:
                        stage_state.retry_count += 1
                        stage_state.error_info = validation.error
                        await self._save_checkpoint(state)
                        continue  # 重试当前阶段
                    else:
                        # 进入人工审核或失败
                        state.current_stage = AdaptationStage.HUMAN_REVIEW
                        await self._save_checkpoint(state)
                        break
                
                # 2.4 更新状态
                stage_state.status = "completed"
                stage_state.output_data = result.serialize()
                stage_state.completed_at = datetime.utcnow()
                state.completed_stages.append(stage)
                state.current_stage = self._next_stage(stage)
                
                # 2.5 保存检查点
                await self._save_checkpoint(state)
                
            except Exception as e:
                stage_state.status = "failed"
                stage_state.error_info = str(e)
                await self._save_checkpoint(state)
                
                # 判断是否可以回退到前一阶段
                if self._can_rollback(state, stage):
                    rollback_target = self._determine_rollback_target(state, stage, e)
                    state.current_stage = rollback_target
                    logger.warning(f"Rolling back from {stage} to {rollback_target}")
                else:
                    state.current_stage = AdaptationStage.FAILED
                    await self._save_checkpoint(state)
                    break
        
        return AdaptationResult(state=state)
    
    async def _execute_with_circuit_breaker(self, mode, input_data, context):
        """带熔断保护的执行"""
        if not self.runtime.circuit_breaker.is_closed(mode.__class__.__name__):
            raise CircuitBreakerOpen(f"Circuit breaker open for {mode.__class__.__name__}")
        
        try:
            return await mode.execute(input_data, context)
        except ModelServiceError as e:
            self.runtime.circuit_breaker.record_failure(mode.__class__.__name__)
            raise
```

### 2.3 为什么需要显式状态机而非 LLM 自驱动？

根据 Azure 架构中心的最佳实践：
> "Don't just rely on the LLM to remember where it is in the process. Use explicit state machines... Store this state externally and load it at the start of each agent turn. If the agent crashes, you can resume exactly where it left off."

**NovelBridge 的具体场景**：
- `storyboard` 阶段生成 24 个 ShotCard 时，第 17 个 shot 因 LLM 上下文超限失败
- 如果没有检查点，需要重新生成全部 24 个
- 有检查点则可以从第 17 个恢复，且已生成的 16 个 ShotCard 的连续性状态被保留

---

## 三、核心 Mode 的 Prompt 工程模板（可直接使用）

### 3.1 plan_episodes 的 Prompt 模板（结构化输出）

```python
# apps/rag-agent/app/adaptation_agent/prompts/plan_episodes.py

PLAN_EPISODES_SYSTEM = """你是一位资深编剧改编顾问。你的任务是将小说章节改编为AI漫剧的分集规划。
你必须严格基于原文证据做改编决策，区分改编类型。

输出必须严格符合以下JSON Schema，不要添加任何额外字段或注释。
思考过程：先分析原文结构，再确定Beat规划，最后绑定证据。"""

PLAN_EPISODES_USER_TEMPLATE = """## 输入信息
### 原著章节
{chapters_text}

### 关键实体（来自知识库）
{entities_json}

### 已有改编约束（人工锁定）
{locked_constraints}

### 输出要求
将上述内容改编为 **1集AI漫剧**（约3-5分钟），输出JSON格式。

## JSON Schema
{{
  "episode_plan": {{
    "title": "string, 本集标题",
    "estimated_duration_seconds": "integer, 预估秒数",
    "adaptation_strategy": "string, 枚举: DIRECT|COMPRESSION|NEW_BRIDGE|HUMAN_ADDED|MODEL_COMPLETION",
    "beats": [
      {{
        "beat_number": "integer",
        "beat_type": "string, 枚举: SETUP|INCITING_INCIDENT|RISING_ACTION|CLIMAX|RESOLUTION",
        "description": "string, 剧情描述",
        "source_chapters": ["string, 来源章节ID"],
        "source_evidence": [
          {{
            "chunk_id": "string",
            "text_span": "string, 原文摘录",
            "adaptation_type": "string, 枚举: DIRECT_QUOTE|COMPRESSED|BRIDGE|ADDED|COMPLETED"
          }}
        ],
        "characters_involved": ["string, 角色名"],
        "estimated_duration": "integer, 预估秒数"
      }}
    ],
    "chapter_coverage": [
      {{
        "chapter_id": "string",
        "coverage_ratio": "float, 0-1, 本章被使用的比例",
        "omission_reason": "string|null, 省略原因"
      }}
    ],
    "complexity_score": "float, 0-1",
    "manual_review_required": "boolean"
  }}
}}

## 关键规则
1. 每个 beat 的 source_evidence 必须包含至少1条原文证据
2. adaptation_type 必须明确标注：
   - DIRECT_QUOTE: 原文直接改编（台词、场景描写）
   - COMPRESSED: 合理压缩（合并对话、省略次要描写）
   - BRIDGE: 新增桥段（连接两个原文场景）
   - ADDED: 人工添加（基于人工输入）
   - COMPLETED: 模型补全（原文未明确，模型推理）
3. 如果 complexity_score > 0.7，manual_review_required 必须为 true
4. 如果检测到角色年龄/服装/形态在章节间有变化，必须在 beats 中标注
"""

# 使用 vLLM/XGrammar 或 OpenAI Structured Output 强制执行此 Schema
```

### 3.2 ShotCard PromptPack 的生成模板（基于 Shot Grammar 框架）

根据 2026 年 Cinematic AI Video Prompt 专家指南，PromptPack 的 `model_outputs["seedance_2.0"]` 应按以下 8 点语法生成：

```python
# apps/rag-agent/app/adaptation_agent/prompts/shot_grammar.py

SHOT_GRAMMAR_TEMPLATE = """基于以下结构化信息，生成符合 Seedance 2.0 语法的视频生成提示词。

## 输入结构化字段
- visual_subject: {visual_subject}
- scene: {scene_description}
- character_refs: {character_refs}
- action: {action}
- emotion: {emotion}
- camera: {camera_json}
- lighting: {lighting_json}
- duration: {duration}
- dialogue: {dialogue}
- sound: {sound}
- continuity_constraints: {continuity_constraints}
- physics_anchors: {physics_anchors}

## 输出格式（Seedance 2.0 语法）
按以下顺序组织，用分号分隔各 Block：

**Subject Block**: {character_refs_formatted} as {visual_subject}, {action}, {emotion}
**Environment Block**: {scene_description}
**Camera & Motion Block**: {camera.lens_type} lens, {camera.shot_type}, {camera.movement}. {camera.stabilization}. {camera.depth_behavior}.
**Lighting & Atmosphere Block**: {lighting.source_type} {lighting.direction}, {lighting.color_temperature}, {lighting.interaction}.
**Physics & Material Response Block**: {physics_anchors_formatted}
**Continuity Block**: {continuity_constraints_formatted}
**Stability Block**: consistent_character_identity, stable_facial_structure, no_temporal_warping

## 示例输出
"A young warrior @Character1 as determined fighter, drawing sword with fierce gaze, micro-expressions of resolve; 
ancient temple courtyard at dawn with mist and stone lanterns; 
35mm anamorphic lens, medium_tracking, slow_dolly_backward. handheld_micro_jitter. shallow_DOF;
volumetric rim_light, 5600K, wet_reflections;
firm_foot_to_ground_contact, fabric_deformation_wind, metal_clang_spark;
wearing red_cloak_and_leather_armor, holding_jade_pendant, morning_light;
consistent_character_identity, stable_facial_structure, no_temporal_warping"

## 约束
- 使用 @Character{N} 格式引用角色参考图
- 不要使用负面提示词（Seedance 不支持），用正面约束语句替代
- 情绪描述必须具体到 micro-expression 级别
- 物理锚点至少包含3个，防止漂浮感
"""
```

---

## 四、连续性状态机的具体算法

### 4.1 ShotContinuityState 的继承与更新算法

这是 `storyboard` 阶段最核心的算法，参考传统影视 Continuity Supervisor 的工作方式：

```python
# apps/rag-agent/app/adaptation_agent/continuity_engine.py

class ContinuityEngine:
    """镜头连续性状态引擎"""
    
    def compute_next_state(
        self,
        prev_shot: Optional[ShotCard],
        current_shot_action: str,
        scene_entry_state: SceneState,
        asset_cards: Dict[str, AssetCard]
    ) -> ShotContinuityState:
        """
        计算当前镜头的连续性状态。
        规则：
        1. 如果是场景第一个镜头，继承 scene_entry_state
        2. 否则继承 prev_shot.continuity_state
        3. 根据 current_shot_action 更新状态
        4. 检查是否有不合理的突变
        """
        
        # 1. 确定基础状态
        if prev_shot is None:
            base_state = scene_entry_state
        else:
            base_state = prev_shot.continuity_state
        
        # 2. 解析动作对状态的影响
        action_effects = self._parse_action_effects(current_shot_action)
        
        # 3. 更新角色位置
        new_char_positions = {}
        for char_id, pos in base_state.character_positions.items():
            if char_id in action_effects.moved_characters:
                # 角色移动了：更新位置，但检查是否合理
                new_pos = action_effects.new_positions.get(char_id, pos)
                # 180度规则：检查是否越轴
                if self._violates_180_rule(pos, new_pos, base_state.camera_direction):
                    new_pos = self._correct_180_violation(pos, new_pos)
                new_char_positions[char_id] = new_pos
            else:
                # 角色未移动：位置保持不变
                new_char_positions[char_id] = pos
        
        # 4. 更新道具状态
        new_prop_states = {}
        for prop_id, prop_state in base_state.prop_states.items():
            if prop_id in action_effects.prop_changes:
                new_prop_states[prop_id] = action_effects.prop_changes[prop_id]
            else:
                new_prop_states[prop_id] = prop_state
        
        # 5. 更新情绪状态
        new_emotion_states = {}
        for char_id, emotion in base_state.emotion_states.items():
            if char_id in action_effects.emotion_changes:
                # 检查情绪跳跃是否过于剧烈
                new_emotion = action_effects.emotion_changes[char_id]
                if self._is_emotion_jump_too_drastic(emotion, new_emotion):
                    # 标记需要人工审核
                    pass
                new_emotion_states[char_id] = new_emotion
            else:
                new_emotion_states[char_id] = emotion
        
        # 6. 确定镜头方向（屏幕方向）
        new_camera_dir = self._determine_camera_direction(
            base_state.camera_direction,
            current_shot_action,
            action_effects
        )
        
        return ShotContinuityState(
            prev_shot_state=prev_shot.id if prev_shot else None,
            character_positions=new_char_positions,
            prop_states=new_prop_states,
            emotion_states=new_emotion_states,
            camera_direction=new_camera_dir,
            screen_direction=self._compute_screen_direction(new_char_positions)
        )
    
    def _violates_180_rule(self, old_pos, new_pos, camera_dir) -> bool:
        """检查是否违反180度轴线规则"""
        # 计算角色移动向量与镜头方向的关系
        move_vector = (new_pos["x"] - old_pos["x"], new_pos["y"] - old_pos["y"])
        # 如果移动导致角色从屏幕左侧跳到右侧（或反之），可能越轴
        dot_product = move_vector[0] * camera_dir["x"] + move_vector[1] * camera_dir["y"]
        return dot_product < -0.5  # 简化判断
    
    def _is_emotion_jump_too_drastic(self, old_emotion: str, new_emotion: str) -> bool:
        """检查情绪跳跃是否合理"""
        # 使用情绪轮（Emotion Wheel）计算情绪距离
        emotion_distance = self.emotion_wheel.distance(old_emotion, new_emotion)
        return emotion_distance > 0.7  # 阈值可调
```

### 4.2 为什么需要这个引擎？

因为 AI 视频生成没有物理演员和场景，模型会"重新想象"每个镜头。如果没有显式状态传递：
- 镜头1：角色 A 在左侧，手持剑
- 镜头2：角色 A 突然在右侧，剑消失了（模型随机生成）
- 镜头3：角色 A 回到左侧，但剑变成了刀

`ContinuityEngine` 通过强制状态继承，确保这些突变被检测并标记为 `ContinuityIssue`。

---

## 五、PromptAdapter 的插件化实现

### 5.1 基于注册表的适配器架构

```python
# apps/rag-agent/app/adaptation_agent/prompt_adapter.py

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel

class PromptAdapter(ABC):
    """多模型提示词适配器基类"""
    
    @property
    @abstractmethod
    def adapter_id(self) -> str:
        pass
    
    @property
    @abstractmethod
    def supported_features(self) -> List[str]:
        """支持的功能列表"""
        pass
    
    @abstractmethod
    def adapt(self, prompt_pack: PromptPack, asset_cards: List[AssetCard]) -> str:
        """将 PromptPack 转换为特定模型的原生格式"""
        pass
    
    @abstractmethod
    def get_reference_format(self, asset: AssetCard) -> str:
        """返回该模型的参考图绑定语法"""
        pass
    
    @abstractmethod
    def estimate_cost(self, prompt_pack: PromptPack) -> float:
        """预估生成成本（美元）"""
        pass

class PromptAdapterRegistry:
    """适配器注册表，支持动态加载"""
    
    _adapters: Dict[str, PromptAdapter] = {}
    
    @classmethod
    def register(cls, adapter: PromptAdapter):
        cls._adapters[adapter.adapter_id] = adapter
    
    @classmethod
    def get(cls, adapter_id: str) -> Optional[PromptAdapter]:
        return cls._adapters.get(adapter_id)
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        return list(cls._adapters.keys())

# Seedance 2.0 适配器实现
class SeedanceAdapter(PromptAdapter):
    adapter_id = "seedance_2.0"
    supported_features = [
        "text_to_video", "image_to_video", "reference_images",
        "audio_sync", "camera_control", "character_consistency"
    ]
    
    def adapt(self, prompt_pack: PromptPack, asset_cards: List[AssetCard]) -> str:
        parts = []
        
        # Subject Block: 角色引用 + 主体 + 动作 + 情绪
        subject_parts = []
        for char_ref in prompt_pack.character_refs:
            asset = next((a for a in asset_cards if a.id == char_ref.asset_id), None)
            if asset:
                ref_tag = self.get_reference_format(asset)
                subject_parts.append(f"{ref_tag} as {char_ref.role_description}")
        subject_parts.append(prompt_pack.visual_subject)
        subject_parts.append(prompt_pack.action)
        subject_parts.append(prompt_pack.emotion)
        parts.append(", ".join(subject_parts))
        
        # Environment Block
        parts.append(prompt_pack.scene_description)
        
        # Camera & Motion Block
        cam = prompt_pack.camera
        camera_str = (
            f"{cam.lens_type} lens, {cam.shot_type}, {cam.movement}. "
            f"{cam.stabilization}. {cam.depth_behavior}."
        )
        parts.append(camera_str)
        
        # Lighting Block
        light = prompt_pack.lighting
        light_str = (
            f"{light.source_type} {light.direction}, {light.color_temperature}, "
            f"{light.interaction}."
        )
        parts.append(light_str)
        
        # Physics Anchors（防止漂浮感）
        if prompt_pack.physics_anchors:
            parts.append(", ".join(prompt_pack.physics_anchors))
        
        # Continuity Constraints
        continuity_parts = []
        for char_id, pos in prompt_pack.continuity_state.character_positions.items():
            continuity_parts.append(f"{char_id}_at_{pos['x']:.1f}_{pos['y']:.1f}")
        if continuity_parts:
            parts.append("; ".join(continuity_parts))
        
        # Stability Tokens（对抗注意力疲劳）
        if prompt_pack.stability_tokens:
            parts.append(", ".join(prompt_pack.stability_tokens))
        
        return ". ".join(parts)
    
    def get_reference_format(self, asset: AssetCard) -> str:
        # Seedance 2.0 使用 @Image{N} 格式
        # 根据 asset 的 reference_image 索引确定 N
        return f"@Image{asset.reference_image_index}"
    
    def estimate_cost(self, prompt_pack: PromptPack) -> float:
        # Seedance 2.0 Pro+ 定价估算
        base_cost = 0.5  # 基础费用
        duration_multiplier = prompt_pack.duration / 5.0  # 按5秒为单位
        return base_cost * duration_multiplier

# Wan/ComfyUI 适配器实现
class WanComfyUIAdapter(PromptAdapter):
    adapter_id = "wan_comfyui"
    supported_features = [
        "text_to_video", "image_to_video", "lora", "controlnet",
        "node_based_workflow", "batch_generation"
    ]
    
    def adapt(self, prompt_pack: PromptPack, asset_cards: List[AssetCard]) -> str:
        # ComfyUI 需要生成 JSON 工作流描述
        return json.dumps({
            "workflow_type": "wan_t2v",
            "positive_prompt": self._build_positive(prompt_pack),
            "negative_prompt": prompt_pack.negative_prompt or "",
            "reference_images": [
                {
                    "image_path": a.reference_images[0].path,
                    "strength": 1.0 if a.asset_type == AssetType.CHARACTER else 0.7
                }
                for a in asset_cards
            ],
            "parameters": {
                "steps": 28,
                "cfg": 7.0,
                "scheduler": "euler_a",
                "width": 1024,
                "height": 576
            },
            "controlnet": {
                "openpose": prompt_pack.camera.pose_reference,
                "depth": prompt_pack.scene.depth_map
            } if prompt_pack.camera.pose_reference else None
        })
    
    def get_reference_format(self, asset: AssetCard) -> str:
        # ComfyUI 使用 [ref:path] 或 IP-Adapter 节点
        return f"[ref:{asset.reference_images[0].path}]"
    
    def estimate_cost(self, prompt_pack: PromptPack) -> float:
        # 自部署成本（GPU时间）
        return 0.05 * prompt_pack.duration  # 粗略估算

# 注册所有适配器
PromptAdapterRegistry.register(SeedanceAdapter())
PromptAdapterRegistry.register(WanComfyUIAdapter())
PromptAdapterRegistry.register(RunwayAdapter())  # 类似实现
PromptAdapterRegistry.register(KlingAdapter())   # 类似实现
```

---

## 六、与现有 NovelBridge 的无缝集成

### 6.1 数据流集成图

```
┌─────────────────────────────────────────────────────────────────┐
│                     PreprocessAgent (已有)                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ Entity      │───→│ Entity      │───→│ ChapterFact │         │
│  │ Governance  │    │ Profile     │    │ (validated) │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  EntityToAssetMapper (新增)                      │
│  - canonical_name → AssetCard.name                             │
│  - entity_type → AssetCard.asset_type                          │
│  - mentions → AssetCard.source_mentions                        │
│  - validated_facts → identity_anchors                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AdaptationAgent (新增)                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ EpisodePlan │───→│ AssetCard   │───→│ SceneCard   │         │
│  │ (beats)     │    │ (+ref imgs) │    │ (+entry_state)│        │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                      │                      │          │
│         ▼                      ▼                      ▼          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ ShotCard    │───→│ PromptPack  │───→│ QC Report   │         │
│  │ (+continuity│    │ (+model     │    │ (+issues)   │         │
│  │  state)     │    │  outputs)   │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Export Package (新增)                         │
│  - episode_plan.json                                           │
│  - asset_cards/ (含 reference images)                           │
│  - scene_cards.json                                            │
│  - shot_cards.json (含 continuity_state)                        │
│  - prompt_packs/ (按模型分目录)                                 │
│  - qc_report.json                                              │
│  - source_evidence_index.json (证据追溯)                        │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 复用现有基础设施

| 现有模块                   | 复用方式 | AdaptationAgent 使用点                         |
| -------------------------- | -------- | ---------------------------------------------- |
| `app/clients/deepseek.py`  | 直接复用 | LLM 推理调用（plan_episodes, storyboard 等）   |
| `app/clients/embedding.py` | 直接复用 | 角色/场景描述的向量缓存                        |
| `app/clients/qdrant.py`    | 直接复用 | 检索相关 chunks 作为证据                       |
| `app/qa/RetrievalRunner`   | 包装复用 | `hybrid_search` 获取原文证据                   |
| `app/pipeline/P1-P8`       | 只读调用 | 获取已治理的 Entity 和 ChapterFact             |
| `app/quality/`             | 扩展复用 | 新增 `ContinuityValidator`                     |
| `app/eval/`                | 扩展复用 | 新增改编质量评测 case                          |
| `app/stores/` (MySQL)      | 新增表   | `adaptation_project`, `episode_plan` 等 7 张表 |
| `app/schemas/`             | 扩展     | 新增 `AdaptationProjectSchema` 等              |

### 6.3 最小侵入性集成原则

**不迁移到 Java**：模型执行、检索、prompt/schema、Agent 编排继续留在 Python。Java Spring Boot 只做：
- 上传入口（小说文件）
- 任务状态查询 API
- Chat/Review API（人工审核界面）
- SSE/WebSocket 进度推送
- 前端聚合

**数据层不变**：
- MySQL 仍然是 source-of-truth
- Qdrant 仍然是主向量库
- Neo4j 仍然只存验证后事实的图投影

---

## 七、实现难点与具体缓解策略

### 7.1 难点 1：长小说上下文超限

**问题**：3-5 章可能仍有数万字，超出 LLM 上下文窗口。

**缓解**：
```python
# 分层摘要策略
class ContextCompressor:
    def compress_for_adaptation(self, chapters: List[Chapter]) -> AdaptationContext:
        # L0: 全书级摘要（已存在）
        book_summary = self.get_book_summary(chapters[0].book_id)
        
        # L1: 章节级摘要（按需生成）
        chapter_summaries = []
        for ch in chapters:
            summary = self.llm.generate(
                prompt=f"用500字总结本章核心剧情、关键事件、角色互动和场景转换：\n{ch.text[:8000]}",
                max_tokens=800
            )
            chapter_summaries.append(summary)
        
        # L2: 精确证据（通过 RAG 按需检索）
        # 不一次性加载所有原文，而是在生成每个 Beat/Shot 时检索相关 chunk
        
        return AdaptationContext(
            book_summary=book_summary,
            chapter_summaries=chapter_summaries,
            retrieval_runner=self.retrieval_runner  # 按需检索
        )
```

### 7.2 难点 2：LLM 生成复杂嵌套 JSON 的可靠性

**问题**：GPT-4 仍有 11.97% 无效响应率，EpisodePlan 的嵌套结构复杂。

**缓解**：
1. **分阶段生成**：先生成 `beats` 列表，再为每个 beat 生成 `source_evidence`
2. **约束解码**：使用 vLLM 的 XGrammar 或 OpenAI 的 `response_format={"type": "json_schema"}` 强制执行
3. **自验证循环**：生成后用 JSON Schema 验证，失败则重试（最多3次）
4. **降级策略**：如果3次都失败，拆分为更小的子任务（如一次只生成1个 beat）

```python
class StructuredGenerator:
    def __init__(self, llm_client, schema_validator):
        self.llm = llm_client
        self.validator = schema_validator
    
    async def generate_with_retry(self, prompt: str, schema: dict, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                # 使用约束解码（如果后端支持）
                raw_output = await self.llm.generate(
                    prompt=prompt,
                    response_format={"type": "json_schema", "schema": schema}
                )
                
                # 解析和验证
                data = json.loads(raw_output)
                self.validator.validate(data, schema)
                
                return data
                
            except (json.JSONDecodeError, ValidationError) as e:
                if attempt < max_retries - 1:
                    # 在 prompt 中添加错误信息，要求修正
                    prompt += f"\n\n【前一次输出有误，请修正】\n错误: {str(e)}\n请重新生成，确保严格符合 JSON Schema。"
                    continue
                else:
                    raise GenerationError(f"Failed after {max_retries} attempts: {e}")
```

### 7.3 难点 3：角色参考图的生成与缓存

**问题**：AssetCard 需要"标准肖像"和"多角度转身图"作为 I2I 输入，但生成这些图需要额外的图像模型调用。

**缓解**：
```python
class AssetImageGenerator:
    """角色参考图生成器"""
    
    async def generate_character_reference_set(self, asset: AssetCard) -> List[ReferenceImage]:
        \"\"\"生成角色的标准参考图集合\"\"\"
        \n        # 1. 正面肖像（最关键，作为身份锚点）
n        portrait = await self.image_model.generate(\n            prompt=f\"Professional character portrait, front-facing, neutral expression, \"\n                   f\"clean background, highly detailed face, {asset.visual_description.subject}\",\n            seed=asset.generation_seed,\n            size=\"1024x1024\"\n        )\n        \n        # 2. 全身照（服装和体型）\n        full_body = await self.image_model.generate(\n            prompt=f\"Full body character shot, standing pose, {asset.visual_description.appearance}, \"\n                   f\"{asset.visual_description.clothing}, clean background\",\n            seed=asset.generation_seed,  # 同 seed 保持一致性\n            size=\"1024x1536\"\n        )\n        \n        # 3. 表情 sheet（4种基本表情）\n        expressions = []\n        for expr in [\"neutral\", \"happy\", \"angry\", \"sad\"]:\n            expr_img = await self.image_model.generate(\n                prompt=f\"Character portrait, {expr} expression, same face as reference, \"\n                       f\"{asset.visual_description.subject}\",\n                seed=asset.generation_seed,\n                reference_image=portrait,  # 使用肖像作为参考\n                size=\"1024x1024\"\n            )\n            expressions.append(expr_img)\n        \n        return [\n            ReferenceImage(type=\"portrait_front\", url=portrait, seed=asset.generation_seed),\n            ReferenceImage(type=\"full_body\", url=full_body, seed=asset.generation_seed),\n            ReferenceImage(type=\"expression_sheet\", url=expressions, seed=asset.generation_seed),\n        ]\n```

### 7.4 难点 4：Seedance 2.0 API 未公开

**问题**：截至 2026 年 5 月，Seedance 2.0 仅 Pro+ 用户可用，无公开 API。

**缓解**：
1. **PromptPack 作为独立产品**：即使不能自动调用 Seedance，结构化 PromptPack 本身就是价值
2. **人工复制测试**：UI 提供"复制 Seedance 格式"按钮，制作团队粘贴到 Seedance 测试
3. **先接入 Wan/ComfyUI**：开源可部署，作为 MVP 的默认视频生成后端
4. **API 监控**：当 Seedance 开放 API 时，只需新增 Adapter，无需改动核心逻辑

---

## 八、数据库 Schema 细化（7张新表）

```sql
-- adaptation_project: 改编项目主表
CREATE TABLE adaptation_project (
    id BINARY(16) PRIMARY KEY,
    book_id BINARY(16) NOT NULL,
    name VARCHAR(255) NOT NULL,
    status ENUM('DRAFT','IN_PROGRESS','REVIEW','LOCKED','EXPORTED') DEFAULT 'DRAFT',
    source_chapters JSON NOT NULL,           -- [chapter_id, ...]
    source_license_status VARCHAR(50),
    adaptation_rights_note TEXT,
    external_ip_style_blocklist JSON,
    likeness_risk_flag BOOLEAN DEFAULT FALSE,
    locked_episode_plan BINARY(16),
    locked_asset_cards JSON,                 -- [asset_id, ...]
    locked_shot_cards JSON,                  -- [shot_id, ...]
    version INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- episode_plan: 分集规划
CREATE TABLE episode_plan (
    id BINARY(16) PRIMARY KEY,
    project_id BINARY(16) NOT NULL,
    episode_number INT NOT NULL,
    title VARCHAR(255),
    adaptation_strategy ENUM('DIRECT','COMPRESSION','NEW_BRIDGE','HUMAN_ADDED','MODEL_COMPLETION'),
    beats JSON NOT NULL,                     -- 复杂嵌套结构，用 JSON
    chapter_coverage JSON,
    source_evidence JSON,                    -- EvidenceBinding 列表
    estimated_duration INT,                  -- 秒
    complexity_score DECIMAL(3,2),
    manual_review_required BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES adaptation_project(id)
);

-- asset_card: 资产卡（角色/场景/道具）
CREATE TABLE asset_card (
    id BINARY(16) PRIMARY KEY,
    project_id BINARY(16) NOT NULL,
    asset_type ENUM('CHARACTER','SCENE','PROP','COSTUME') NOT NULL,
    name VARCHAR(255) NOT NULL,
    version INT DEFAULT 1,
    version_history JSON,                    -- 版本历史快照
    visual_description JSON NOT NULL,        -- 结构化视觉描述
    reference_images JSON,                   -- [{type, url, seed}, ...]
    source_entity_id BINARY(16),             -- 关联 entities 表
    source_mentions JSON,                    -- [{chapter_id, chunk_id, text}, ...]
    identity_anchors JSON,                   -- [\"red hair\", \"scar on left cheek\", ...]
    mutable_attributes JSON,                 -- [\"clothing\", \"expression\", ...]
    status ENUM('DRAFT','CONFIRMED','LOCKED','DEPRECATED') DEFAULT 'DRAFT',
    locked_by VARCHAR(255),
    generation_seed INT,
    model_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES adaptation_project(id)
);

-- scene_card: 场次卡
CREATE TABLE scene_card (
    id BINARY(16) PRIMARY KEY,
    episode_plan_id BINARY(16) NOT NULL,
    scene_number INT NOT NULL,
    title VARCHAR(255),
    setting VARCHAR(255),
    time_of_day VARCHAR(50),
    location VARCHAR(255),
    characters_present JSON,                 -- [{asset_id, role}, ...]
    props_present JSON,                      -- [{asset_id, state}, ...]
    plot_summary TEXT,
    emotional_tone VARCHAR(100),
    narrative_purpose TEXT,
    shots JSON,                              -- [shot_id, ...]
    entry_state JSON,                        -- SceneState 对象
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (episode_plan_id) REFERENCES episode_plan(id)
);

-- shot_card: 分镜卡（核心表）
CREATE TABLE shot_card (
    id BINARY(16) PRIMARY KEY,
    scene_card_id BINARY(16) NOT NULL,
    shot_number INT NOT NULL,
    shot_type ENUM('WIDE','MEDIUM','CLOSE_UP','EXTREME_CLOSE_UP','POV','ESTABLISHING','INSERT'),
    description TEXT,
    action TEXT,
    dialogue TEXT,
    narration TEXT,
    continuity_state JSON NOT NULL,        -- ShotContinuityState 对象
    prompt_pack_id BINARY(16),               -- 关联 prompt_pack 表
    estimated_generation_cost DECIMAL(10,4),
    difficulty_level INT CHECK (difficulty_level BETWEEN 1 AND 5),
    retry_risk DECIMAL(3,2),
    model_recommendation VARCHAR(50),
    manual_review_required BOOLEAN DEFAULT FALSE,
    status ENUM('DRAFT','PREPARED','LOCKED','GENERATED','APPROVED') DEFAULT 'DRAFT',
    source_evidence JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (scene_card_id) REFERENCES scene_card(id)
);

-- prompt_pack: 多模型提示词包
CREATE TABLE prompt_pack (
    id BINARY(16) PRIMARY KEY,
    shot_card_id BINARY(16) NOT NULL,
    visual_subject TEXT,
    scene_description TEXT,
    character_refs JSON,                     -- [{asset_id, tag, role_description}, ...]
    action TEXT,
    emotion TEXT,
    camera JSON,                             -- CameraSpec 对象
    lighting JSON,                           -- LightingSpec 对象
    duration INT,
    dialogue TEXT,
    sound TEXT,
    negative_prompt TEXT,
    reference_binding JSON,                  -- [{asset_id, slot, strength}, ...]
    physics_anchors JSON,
    stability_tokens JSON,
    model_outputs JSON,                      -- {seedance_2.0: \"...\", wan: \"...\", ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shot_card_id) REFERENCES shot_card(id)
);

-- continuity_issue: 连续性问题
CREATE TABLE continuity_issue (
    id BINARY(16) PRIMARY KEY,
    project_id BINARY(16) NOT NULL,
    issue_type ENUM('CHARACTER_DRIFT','PROP_MISMATCH','SCENE_INCONSISTENCY',
                    'TIMELINE_ERROR','EYELINE_MISMATCH','SCREEN_DIRECTION_VIOLATION',
                    'EMOTION_JUMP','COSTUME_ERROR') NOT NULL,
    severity ENUM('CRITICAL','HIGH','MEDIUM','LOW') NOT NULL,
    affected_shots JSON,
    affected_assets JSON,
    description TEXT,
    expected_state TEXT,
    actual_state TEXT,
    suggested_fix TEXT,
    auto_fixable BOOLEAN DEFAULT FALSE,
    status ENUM('OPEN','ACKNOWLEDGED','FIXED','WONTFIX') DEFAULT 'OPEN',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES adaptation_project(id)
);

-- adaptation_run: 改编运行记录（用于状态机恢复）
CREATE TABLE adaptation_run (
    id BINARY(16) PRIMARY KEY,
    project_id BINARY(16) NOT NULL,
    current_stage VARCHAR(50),
    completed_stages JSON,
    stage_states JSON,                       -- 完整状态快照
    locked_entities JSON,
    global_context JSON,
    status ENUM('RUNNING','PAUSED','COMPLETED','FAILED') DEFAULT 'RUNNING',
    checkpoint_data TEXT,                    -- 序列化的 AdaptationState
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES adaptation_project(id)
);
```

---

## 九、下一步具体行动建议

### 立即可以做（本周）：
1. **创建 `docs/16-ai-drama-direction.md`**：用我上面提供的架构图和文字描述
2. **创建 `docs/17-adaptation-agent-contract.md`**：定义 Mode 接口、输入输出、错误码
3. **评审数据库 Schema**：用上面的 SQL 在 MySQL 中创建表，测试字段是否满足查询需求
4. **Prompt 模板草稿**：用我提供的 `PLAN_EPISODES_SYSTEM` 和 `SHOT_GRAMMAR_TEMPLATE` 做第一次 LLM 调用测试

### 短期（2-3周）：
5. **实现 `AdaptationState` + `StateStore`**：基于现有 MySQL client，做序列化/反序列化
6. **实现 `PlanEpisodesMode` 骨架**：只做分集规划，不做后续阶段，验证端到端流程
7. **实现 `EntityToAssetMapper`**：连接 PreprocessAgent 的 Entity Profile 和新的 AssetCard

### 中期（1-2月）：
8. **实现 `StoryboardMode` + `ContinuityEngine`**：这是最复杂的部分，需要反复调试
9. **实现 `PromptAdapterRegistry` + `SeedanceAdapter`**：即使不能调用 API，也要能输出正确格式的 prompt
10. **UI 工作台原型**：用 Java Spring Boot 做任务状态页面，Python 暴露 `/api/adaptation/{id}/status` SSE 接口

---

## 十、总结：NovelBridge Stage 4 的核心竞争力

| 维度            | 竞品做法      | NovelBridge 差异化                           |
| --------------- | ------------- | -------------------------------------------- |
| **输入处理**    | 接收剧本/脚本 | **接收长篇小说原文，深度理解**               |
| **角色一致性**  | 简单参考图    | **I2I Seed Frame + 身份锚点 + 多角度转身图** |
| **改编可追溯**  | 黑盒生成      | **每步绑定原文证据，区分改编类型**           |
| **连续性**      | 人工检查      | **显式状态机 + 算法检测 + 自动修复建议**     |
| **Prompt 工程** | 单字符串      | **结构化 PromptPack + 多模型适配器**         |
| **人工协作**    | 事后修改      | **人工锁定前置，系统尊重锁定**               |
| **输出**        | 视频文件      | **结构化生产包（可审核、可编辑、可导出）**   |

你的方向是正确的：**不做"一键成片"的玩具，做"证据化改编系统"的生产工具**。这个定位在 AI 漫剧制作的上游有真实的稀缺性。

如果你需要我针对某个具体 Mode（如 `storyboard` 或 `qc_continuity`）展开更详细的代码设计，或者需要我帮你写某份文档的完整草稿，请告诉我。