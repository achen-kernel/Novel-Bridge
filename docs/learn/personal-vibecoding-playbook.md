# 个人 Vibe Coding 工作法

本文件沉淀你在使用 AI coding agent 时形成的个人规则。只记录有证据、能复用的经验，不写长教程。

## 当前阶段流程

1. 先定义一个小型可验证 stage。
2. 明确本阶段 In / Out / Evidence / Risks。
3. 要求 agent 说明可能修改哪些文件。
4. 完成前必须提供构建、测试、接口、页面或手工验证证据。
5. 不再默认生成 practice 副本；学习资产改为 route marker、harness evidence、retro 和 playbook。
6. 出现 Bug 或 Agent 偏差时，记录成下次提示规则。
7. 每轮完成后要求 agent 核对 stage harness：status → route → readiness → implement → evidence → harden → mark → retro。
8. 当一个 stage 同时包含部署、模型、图谱、向量库、前端、QA、微调等多条线时，先拆成可验收子阶段。
9. 重要代码只打路线标注，不打练习标注：`@NB-ENTRYPOINT`、`@NB-AGENT-STEP`、`@NB-MODEL-CALL`、`@NB-EVIDENCE`、`@NB-DATA-WRITE`、`@NB-RISK`、`@NB-ROADMAP`。

## 新增规则：管线参数联动检查

| 规则 | 证据 | 置信度 | 适用场景 |
|---|---|---|---|
| **修改管线参数时必须扫描整个依赖链，不能单点修复** | `use_model=true` 改了但没查 `ctx-size`→400；`ctx-size` 改了没查 `max_tokens`→截断；每个修复都产生新问题 | **critical** | 所有涉及模型/管线/配置的修改 |
| **修复流程：列链路 → 联动检查 → 重启服务 → 端到端验证** | 从管线的反复失败提炼的修复模板 | high | 模型参数、部署配置、环境变量 |

### 参数联动检查清单

修改模型/管线参数时，依次检查以下链路中的每个节点：

```
[参数改动]
    ↓
1. ctx-size（上下文窗口）← 影响所有输入输出总长
2. max_tokens（输出上限）← ctx-size 减去 input_tokens 后的余量
3. temperature（创造力）← 与 max_tokens 协同，高 temperature 需要更多 tokens
4. chat_template / prompt_template（模板引擎）← 与参数格式兼容性
5. .env / config.py（配置源）← 参数是否同步到所有配置文件
6. systemd restart / docker restart（服务重载）← 配置是否已加载
7. health check → 最小请求测试 → 全量运行（验证链条）
```

每次改任何参数，跑一遍这个清单。

## 我的 Agent 提示规则

| 规则 | 证据 | 置信度 | 适用场景 |
|---|---|---|---|
| 先 demo 再扩展，不要一开始铺满 20 张表 | demo-0 阶段收口时发现文档规划重于可运行反馈 | high | 新项目、复杂功能、AI/RAG 项目 |
| 项目结构不符合脚本默认假设时，先写 adapter，不强行改项目结构 | 后端位于 `Novel-Bridge/` 子目录，早期 `vtl_scan.py` 误判 | high | 多服务仓库、嵌套后端项目 |
| **每轮完成后要求 agent 做代码注释审查** | Demo 1/2 结束后发现实体类没有注释、算法没有解释 | high | 任何 agent 生成的代码 |
| **每个 demo 完成后要求 agent 列出未执行的 skill 步骤** | Demo 1 完成后 retro/practice/skill 全部跳过，未被追踪 | high | 使用 vibe-learn skill 的所有对话 |
| **App 启动后先用 ApiFox 或 Invoke-RestMethod 验证，避免 shell curl 踩坑** | PowerShell curl 导致 JSON 解析失败，浪费定位时间 | medium | Windows PowerShell 环境 |
| **大需求先拆子 demo，再允许实现** | Demo 5 同时包含远程部署、模型、GBNF、Neo4j、向量库、QA、微调，若不拆分会变成大而全平台实现 | high | AI/RAG、部署、全栈、跨服务项目 |
| **Practice 可以跳过，但跳过要有证据** | 远程部署和 GBNF 阶段强行找 Java 练习代码价值低，closing 脚本已改为 practice decision | high | 基础设施、Prompt、文档、服务编排阶段 |
| **服务脚本显示成功后，要区分“脚本启动成功”和“已有服务被检测到”** | `nb_up.sh` 在 Docker 权限不足时仍因已有容器端口开放而显示 UP；加入 docker 组并重新登录后才完成权限闭环 | high | 远程部署、一键启动脚本、Docker Compose |
| **Python 练习要从真实项目代码里挑，不单独刷题** | Demo 5 开始出现 `rag-agent`、Chroma、LLM 调用、数据抽取和部署脚本，这些比孤立语法练习更贴近项目能力 | high | Python 服务、数据处理、RAG、LLM 工程、自动化脚本 |
| **每次遇到边界转换问题（编码、时区、换行符、序列化、collation 等）主动记录到 pitfall 文档，并提炼成 playbook 规则** | Demo 5B TXT 编码问题，Java 写入 MySQL 前未检测编码导致远端全链路乱码，修复成本高 | high | 跨语言数据交换、远程协作、文件上传处理 |
| **agent 在对话中发现新的经验教训时，不等用户提醒，主动写入 pitfall 文档和 playbook** | 编码转换、重复上传去重、Docker 权限、MySQL 密码重建等多个坑在对话中被逐步发现，逐个记录后才形成完整文档 | high | 任何涉及配置、部署、跨系统协作的对话 |
| **AI 阅读 Agent 先做 Evidence-first RAG，再做 GraphRAG** | AI Reader 的别名、泛称、关系泛化和全局高亮问题说明图谱会放大脏数据 | high | NovelBridge 新版 RAG、图谱、问答 |
| **UTF-8/utf8mb4 是内部标准，输入编码只在 ingestion 解码一次** | 中文 TXT 可能是 GB18030/GBK，但内部存储和模型处理需要统一 Unicode，避免远端无法修复的乱码 | high | 文件上传、数据库写入、Python/Java 交互 |
| **Practice 副本不是当前项目主线，route marker 和 harness evidence 才是主线** | 复杂 AI 工程更需要回看关键路线、模型调用、证据校验和踩坑闸门，而不是 TODO 练习副本 | high | Stage 0 之后所有阶段 |

## 新增规则：LLM JSON 输出必须加 Grammar 约束

| 规则 | 证据 | 置信度 | 适用场景 |
|---|---|---|---|
| **LLM 输出结构化数据时，必须用 grammar 约束，不能只靠 prompt** | Qwen3.5-9B 输出 JSON 缺逗号、key 名不符预期、格式自由发散，prompt 暗示完全不够 | **critical** | 所有 LLM JSON 输出场景 |
| **数据链路 key 名必须端到端一致** | prompt 写 `entities`、管线读 `entity_mentions`、84 分钟无声失败 | high | 模型 pipeline、数据提取、序列化/反序列化 |
| **批量任务完成后必须抽样验证内容，不能只看计数** | 102/102 success 但实际数据全部被丢 | high | 批量提取、模型批量调用、数据集生成 |

### LLM JSON 输出三件套

任何需要 LLM 输出结构化 JSON 的场景，必须同时做：

1. **Prompt 给出精确 JSON 模板**（字段名、嵌套关系、类型都要明确）
2. **GBNF grammar 文件**（服务端约束 token 生成，杜绝非法 JSON）
3. **健壮的解析 + 可观测的 fallback**（解析失败不能静默吞数据，必须 log + 有迹可循）

## 我的薄弱点

| 主题 | 证据 | 下一步练习 |
|---|---|---|
| 从大设计收敛到小 demo | 表设计和计划较完整，但代码仍是骨架 | Demo 1 只实现 Book/Chapter 导入 |
| Harness 工程落地 | 理解概念后还需要在代码中实现 AgentRun/AgentStep/Citation | Demo 2/3 专门练状态与引用链路 |
| **督促 agent 走完完整循环** | 两次 demo 结束后都漏了 retro/practice，需要用户手动提醒 | 加入提示规则，形成习惯 |
| **控制复杂项目范围** | Demo 5 文档自然扩张到完整 GraphRAG 平台，需要主动拆阶段 | 每次让 agent 先写“本阶段不做什么”和验收证据 |
| **MyBatis → MyBatis-Plus 渐进升级（本地端）** | 当前 Mapper 已使用 MyBatis 注解模式（@Insert/@Select），后续计划升级到 MyBatis-Plus 获得动态 QueryWrapper、Lambda 查询和分页能力。Demo 6/7 前可以考虑迁移以便简化查询代码 | 当出现复杂动态 SQL 或多表分页查询时，引入 mybatis-spring-boot-starter 并逐步替换 Mapper |

## 新增规则：Pipeline 部署与调试（2026-05-21）

| 规则 | 证据 | 置信度 | 适用场景 |
|---|---|---|---|
| **FastAPI POST 必须传 body（`{}` 或有效 JSON）** | 5 本书全报 422 | 高 | 任何 FastAPI POST 调用 |
| **新增 DB 列/表后必须手动同步远端** | `rules_json` 缺失导致 500 | 高 | schema 变更 |
| **httpx 同步调用在等待期间不输出 log** | 多次被误判为卡死 | 高 | 长时间 API 调用 |
| **`use_model=True` 提取每 chunk 18-60s** | 实际多次计时 | 中 | 预估耗时 |
| **大书（>100 章）放最后跑** | Book 6 102 章阻塞后续 | 中 | 多书 Pipeline |
| **代码修改必须重启 uvicorn** | 无 hot reload | 高 | 调试 |
| **Windows 端口 TIME_WAIT 需等 30-60s 或换端口** | `Errno 10048` 多次出现 | 高 | 频繁启停 |
| **管道脚本写成 `.py` 文件而非 inline** | PowerShell 引号冲突 | 高 | 任何 Python 执行 |
| **embedding 模型不能异步调用，必须卸到线程池** | `asyncio.to_thread` 解决 uvicorn 事件循环阻塞 | **critical** | sentence-transformers / PyTorch 推理 |
| **embedding 模型启动时预加载（主线程），避免工作线程 MKL 混乱** | 16 核跑满、系统卡死 | 高 | SentenceTransformer 加载 |
| **整个 index 流程（embed + Qdrant 写入）必须同步在线程池执行** | 尝试部分异步修复无效 | 高 | Qdrant 批量写入 |
| **远端起服务必须先杀旧进程再启动** | `address already in use` 实际跑的是旧代码 | 高 | 重启部署 |
| **sentence-transformers batch 不能太大，建议 5 条** | 35 条一次全量 CPU burst 导致进程崩 | 中 | embedding 索引 |
| **chunk 文本 > 45000 字符时截断防止 OOM** | 21584 bytes × 35 ≈ 内存溢出 | 中 | embedding 预处理 |

## Skill 改进候选

真正要修改 skill 时，先在 `vtl-feedback-log.md` 记录证据，再集中迭代。
## Demo answer presentation rule

| Rule | Evidence | Confidence | Applies to |
|---|---|---|---|
| **Evidence-first does not mean evidence-as-answer** | Stage 6C demo exposed raw chunk excerpts and relation records as the visible answer, making the product look like a retrieval dump instead of a reading agent | high | ReaderAgent answer/analyze/trace UI and API presentation |
| **RAG route should be retrieve -> model synthesize -> support-check -> cite/debug** | User-facing answer quality improved only after treating evidence as model input and moving raw excerpts to evidence/debug views | high | Any novel QA, character analysis, relation timeline, and future authoring support |
| **Do not over-template model answers in demos** | A strict 3-5 sentence rule made output safe but mechanical; better constraint is natural answer first, no unsupported facts, no raw excerpt dumping | medium | Portfolio demos and product-facing LLM responses |

## ReaderAgent planning and answer quality rules

| Rule | Evidence | Confidence | Applies to |
|---|---|---|---|
| **Mode selection should be planned by the system, not forced onto the user** | In demo testing, `answer`/`analyze`/`trace` were meaningfully different, but the user could not reliably know which one to choose for vague reading tasks | high | ReaderAgent UX, future product API aggregation |
| **`auto` is a planning-layer concept, not a backend ReaderMode** | `/api/reader-agent/run` remains stable by converting smart selection into an existing mode before execution | high | API compatibility and frontend planning |
| **Question optimization is part of RAG quality** | Vague prompts need target extraction and intent rewriting before retrieval; otherwise the model may answer the wrong task shape | high | QA, analyze, trace, eval case design |
| **Local 9B output should be treated as draft-quality unless audited** | 9B captured the 山海经 answer skeleton but had punctuation defects, repetition, and broad claims; DeepSeek produced a cleaner final answer from the same knowledge base | high | Provider selection, answer polish, portfolio demos |
| **Separate retrieval evaluation from answer-writing evaluation** | Same evidence can lead to different answer quality across providers, so retrieval metrics alone do not prove final user-answer quality | high | Eval expansion and model comparison |
| **Answer polish should clean formatting and unsupported claims without changing evidence** | Needed for citation tag removal, chunk id cleanup, punctuation cleanup, repetition compression, and broad-claim warnings | medium | Future ReaderAgent answer polish/audit layer |
| **A mode demo is not yet a full agent** | Stage 6C can run `answer/analyze/trace/enrich`, but still lacks durable session memory, follow-up resolution, backend planning, and tool orchestration | high | ReaderAgent roadmap and portfolio explanation |
| **Design ReaderAgent like an orchestrated coding agent, not a single prompt** | A coding agent plans, selects tools, keeps working memory, records trace, handles follow-up, and audits output; ReaderAgent should adopt the same pattern for reading/analysis tasks | high | Stage 6E+ planning, memory, tool calls, trace inspector |
| **Provider prompts should be different by model role** | 9B needs stricter structure and cleanup; DeepSeek is better for final rewrite, follow-up, and audit | high | Model prompt design and eval |
| **Backend planner should be the canonical logic source; frontend rules are fallback** | Stage 6E moved smart selection logic from JS to Python; 18 backend tests replaced untestable frontend rules | high | Any demo logic shared between frontend and backend |
| **Answer cleanup (citation tags, punctuation, ids) should be pure functions, not model calls** | `answer_polish.py` does deterministic cleanup without model calls; testable, provider-independent | high | Model output post-processing |
| **Session memory for demo should be in-memory, not DB-backed** | DB-backed sessions add schema/migration complexity; in-memory avoids MySQL reconnect issues | high | Demo session management |
| **Reference resolution (pronouns, "这关系", "这条线索") should be heuristic first, not model-based** | "他" always resolves to current_target_name in session context; model-based resolution is future work | medium | Follow-up question handling |
| **Answer post-processing should be in agent.py, not duplicated in each mode runner** | `_post_process()` wraps every mode runner once; prevents forgetting polish on new modes | high | Agent architecture, code maintainability |
| **Broad claim detection is pattern-based; accept false positives** | Pattern matching catches "古代百科全书", "最重要的" etc. without LLM cost; precision over recall | medium | Answer audit, demos |
| **Planner should produce request_patch, not modify run payload directly** | Keeps planner read-only, stateless, safe; caller decides how to merge | high | API design, safety boundaries |
| **Entity target collection in planner should capture all known targets, not only the primary** | "追踪宋江成为梁山核心的关键线索" correctly returns both "宋江" and "梁山"; narrowing is a downstream concern | medium | Target detection, test design |
| **Orchestration patterns need end-to-end tests, not just schema/registry tests** | tool_sequence existed in PlannerResponse but /run never consumed it; _default_sequence existed but dropped fields | high | Runtime closure, staging |
| **Cross-model review cycles are effective for wiring bugs** | First fix round fixed visible bugs; second model review found deeper structural gaps (no orchestration run, no DB tool_calls) | high | Quality assurance, code review |
| **Top-level orchestration run should be created before tool execution** | Without explicit orchestration run_id, tool calls can't share trace context and audit/polish steps are invisible in Trace Inspector | high | Agent architecture |
