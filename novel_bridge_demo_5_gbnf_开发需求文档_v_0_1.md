# NovelBridge-Agents Demo 5 与后续开发需求文档 v0.1

## 0. 文档定位

本文档用于明确 NovelBridge-Agents 的 Demo 5 开发边界、核心功能、技术路线、GBNF 结构化抽取方案，以及后续 Demo 6/7 和开源复用方向。

Demo 5 的目标不是一次性完成完整 GraphRAG，而是先完成远程部署、chunk、llama.cpp + GBNF 实体抽取、候选入库和最小人工审核闭环。完整关系/事件/Claim、Neo4j 深化、向量检索和带引用 QA 可以拆到 Demo 6/7。

---

## 1. 项目总目标

NovelBridge-Agents 是一个本地优先的小说/书籍智能阅读与分析系统。

核心流程：

```text
导入书籍
  → 章节切分
  → 文本分块
  → 本地模型抽取实体、事件、关系、证据
  → GBNF/JSON Schema 约束输出
  → JSON 校验与候选数据入库
  → 人工审核
  → 审核通过的数据进入 Neo4j / 向量库 / 检索索引
  → 在线问答时基于图谱、原文片段和引用证据回答
```

系统原则：

1. 模型只产生候选，不直接产生最终真相。
2. 事实存储在 MySQL、Neo4j、向量库和原文证据中，不存进模型权重。
3. 离线建书可以慢，在线问答必须尽量快。
4. 每条实体、关系、事件、结论都必须能追溯到原文证据。
5. 人工审核是核心流程，不是可有可无的后台功能。
6. Demo 5 必须为后续微调、评测、开源复用积累数据。
7. GBNF 是 Demo 5 的核心能力之一，而不是后续优化项。

---

## 2. Demo 5 的一句话定义

Demo 5 要实现：

> 远程 Linux 上跑通 MySQL、Neo4j、向量库、llama.cpp 和 Python `rag-agent`；一本书从已有章节进入 chunk 生成，再通过 llama.cpp + GBNF/JSON Schema 约束生成实体候选，保存 `model_run`、candidate 和 review 记录，并能在前端完成最小人工审核。

Demo 6 再扩展为事件/关系/Claim 和 Neo4j 图谱增强。  
Demo 7 再扩展为 GraphRAG QA、评测和微调数据准备。

---

## 3. Demo 5 必须完成的范围

### 3.1 必做功能

#### 3.1.1 书籍导入与章节切分

输入：

- TXT
- Markdown
- 简单 EPUB，后续再做

输出：

- book
- chapter
- chunk

章节切分要求：

- 支持“第X回”“第X章”“Chapter X”等常见格式。
- 章节切分失败时允许人工指定章节边界。
- 每个 chapter 保留原始文本、清洗文本、字符范围、顺序号。

#### 3.1.2 Chunk 生成

chunk 不应只按固定 token 截断，应保留小说叙事上下文。

建议规则：

```text
chunk_size: 800-1500 中文字左右
chunk_overlap: 150-300 中文字
chapter_boundary: 不跨章
paragraph_boundary: 优先不打断自然段
```

每个 chunk 保存：

```text
chunk_id
book_id
chapter_id
chunk_index
start_char
end_char
raw_text
clean_text
token_count
created_at
```

#### 3.1.3 llama.cpp 本地推理接入

Demo 5 优先使用 llama.cpp。

推荐服务模式：

```text
llama-server
  → OpenAI-compatible endpoint
  → rag-agent 调用
  → Spring Boot 记录任务状态和结果
```

不建议直接把所有模型调用逻辑写死在 Spring Boot 中。更稳的方式是新增一个轻量 Python `rag-agent` 服务：

```text
Spring Boot：业务系统、任务调度、MySQL、用户接口
rag-agent：Prompt 构造、llama.cpp 调用、GBNF/JSON Schema、解析校验、重试
Neo4j：图谱存储
Vector Store：向量检索
```

#### 3.1.4 GBNF 约束抽取

这是 Demo 5 的重点。

目标：

- 避免 JSON 格式错误。
- 避免多余解释文字。
- 避免 Markdown 包裹 JSON。
- 避免字段缺失、字段乱名。
- 降低小模型/量化模型输出崩坏概率。
- 为单张 3090 或更低配用户提供可复用方案。

GBNF 的原则：

1. 第一阶段不要追求过于复杂的嵌套结构。
2. 字段必须固定。
3. 枚举值必须收窄。
4. 字符串长度应在后处理层控制，GBNF 主要负责结构。
5. 数组数量最好有上限，避免小模型无限生成。
6. Prompt 负责语义，GBNF 负责语法。

#### 3.1.5 抽取任务类型

Demo 5 推荐先拆成多个小抽取任务，不要一次性抽所有东西。

建议顺序：

```text
任务 A：实体抽取
任务 B：事件抽取
任务 C：关系抽取
任务 D：Claim/证据抽取
任务 E：QA 引用回答
```

不要一开始就让模型输出一个巨大的：

```json
{
  "entities": [],
  "events": [],
  "relations": [],
  "claims": []
}
```

原因：

- 小模型容易乱。
- 长 JSON 容易截断。
- 审核粒度太粗。
- 失败后重试成本高。

Demo 5 第一版只要求实体抽取闭环。事件、关系、Claim 和 QA grammar 可以先设计 schema，但实现放到 Demo 6/7。

---

## 4. 推荐的 Demo 5 数据流

```text
1. 用户导入书籍
2. Spring Boot 创建 book_import_task
3. 文本清洗与章节切分
4. 生成 novel_chapter / novel_chunk
5. Spring Boot 创建 extraction_run
6. rag-agent 读取 chunk
7. rag-agent 构造 Prompt + GBNF/JSON Schema
8. llama.cpp 生成结构化 JSON
9. rag-agent 进行 JSON parse + Schema validate
10. 原始 prompt/output/错误写入 novel_model_run
11. 合法实体结果写入 candidate 表
12. 前端 review UI 展示候选实体
13. 人工审核通过后写入 Neo4j 最小 Entity/Chunk/Chapter 图谱
```

Demo 6 扩展：

```text
relation/event/claim extraction
entity merge / alias management
Neo4j relationship write
vector index
```

Demo 7 扩展：

```text
BM25 + vector retrieval
graph expansion
QA answer with citation
evaluation and fine-tuning data export
```

---

## 5. MySQL 与 Neo4j 分工

### 5.1 MySQL 负责

MySQL 是业务、审计、状态和原始记录中心。

建议表：

```text
novel_book
novel_chapter
novel_chunk
novel_agent_run
novel_agent_step
novel_model_run
novel_extraction_candidate
novel_review_record
novel_chat_session
novel_chat_message
novel_citation
novel_prompt_template
novel_grammar_template
```

MySQL 必须保留：

- 每次模型调用的 prompt
- 使用的模型名称
- 使用的 grammar/schema 版本
- 原始输出
- 解析是否成功
- 错误类型
- 重试次数
- 人工修改记录
- 最终审核状态

### 5.2 Neo4j 负责

Neo4j 是审核通过后的知识图谱中心。

节点：

```cypher
(:Book)
(:Chapter)
(:Chunk)
(:Entity)
(:Event)
(:Claim)
```

关系：

```cypher
(:Entity)-[:APPEARS_IN]->(:Chapter)
(:Entity)-[:MENTIONS_IN]->(:Chunk)
(:Entity)-[:PARTICIPATES_IN {role}]->(:Event)
(:Event)-[:HAPPENS_IN]->(:Chapter)
(:Event)-[:SUPPORTED_BY]->(:Chunk)
(:Claim)-[:SUPPORTED_BY]->(:Chunk)
(:Claim)-[:MENTIONS]->(:Entity)
(:Entity)-[:RELATED_TO {relation_type, confidence, status}]->(:Entity)
```

每条关系都应保留：

```text
source_chapter_id
source_chunk_id
evidence_text
confidence
extraction_model
grammar_version
prompt_version
status
reviewer
reviewed_at
```

---

## 6. Demo 5 抽取 Schema 设计

### 6.1 实体类型

第一版不要太复杂。

```text
CHARACTER：人物
LOCATION：地点
ITEM：物品/法宝/武器/重要物件
ORG：组织/门派/国家/势力
TITLE：称号/身份
UNKNOWN：不确定类型
```

### 6.2 实体候选字段

```json
{
  "entity_id": "临时ID",
  "name": "实体名称",
  "type": "CHARACTER",
  "aliases": ["别名1", "别名2"],
  "description": "基于当前片段的简短描述",
  "evidence_text": "原文证据",
  "confidence": 0.85,
  "uncertain": false
}
```

注意：

- entity_id 是临时 ID，不是最终图谱 ID。
- description 只能基于当前 chunk，不允许跨章编造。
- aliases 只能来自原文或非常明显的称呼。

### 6.3 事件字段

```json
{
  "event_id": "临时ID",
  "event_type": "MEET|MOVE|FIGHT|DIALOGUE|DISCOVERY|TRANSFORMATION|DEATH|OTHER",
  "summary": "事件摘要",
  "participants": ["孙悟空", "唐僧"],
  "location": "地点名或空字符串",
  "time_hint": "时间提示或空字符串",
  "evidence_text": "原文证据",
  "confidence": 0.8,
  "uncertain": false
}
```

### 6.4 关系字段

```json
{
  "source": "实体A",
  "target": "实体B",
  "relation_type": "MASTER_OF|APPRENTICE_OF|ALLY_OF|ENEMY_OF|FAMILY_OF|LOCATED_IN|OWNS|OTHER",
  "direction": "A_TO_B",
  "evidence_text": "原文证据",
  "confidence": 0.8,
  "uncertain": false
}
```

### 6.5 Claim 字段

Claim 是“可被引用的事实性判断”。

```json
{
  "claim": "孙悟空拜菩提祖师为师。",
  "mentioned_entities": ["孙悟空", "菩提祖师"],
  "evidence_text": "原文证据",
  "confidence": 0.9,
  "uncertain": false
}
```

---

## 7. GBNF 方案

### 7.1 为什么 Demo 5 应该优先做 GBNF

普通 Prompt 的问题：

```text
模型可能输出解释文字
模型可能输出 Markdown
模型可能漏字段
模型可能多字段
模型可能 JSON 引号错误
模型可能中文标点导致 parse 失败
模型可能在长上下文下输出乱码
```

GBNF 的价值：

```text
在采样层限制模型只能生成符合语法的内容
让 JSON 结构错误显著减少
让低参数、低量化模型也能更稳定完成抽取
把“格式正确性”从 Prompt 工程转移到底层约束
```

但要注意：

```text
GBNF 只能保证形式，不保证语义正确。
语义正确仍然依赖 Prompt、上下文、验证器和人工审核。
```

### 7.2 Demo 5 的 GBNF 策略

推荐三层结构：

```text
第一层：通用 JSON Grammar
第二层：任务专用 JSON Schema → GBNF
第三层：手写强约束 GBNF，用于核心抽取任务
```

开发顺序：

```text
v0.1：使用 llama.cpp json_schema / response_format，让输出符合固定 JSON Schema
v0.2：将 JSON Schema 转为 GBNF 文件，加入版本管理
v0.3：为 entity/event/relation 三个任务分别手写 GBNF，提高稳定性和速度
v0.4：整理成开源模板，提供低配模型版本
```

### 7.3 不建议第一版使用过复杂 GBNF

不要一开始就把所有实体、事件、关系、Claim 放进一个巨大 GBNF。

推荐：

```text
entity_extract.gbnf
relation_extract.gbnf
event_extract.gbnf
claim_extract.gbnf
qa_citation.gbnf
```

每个 grammar 都独立测试。

### 7.4 实体抽取 GBNF 示例草案

下面是概念草案，实际开发时还要根据 llama.cpp validator 测试微调。

```gbnf
root ::= "{" ws "\"chapter_id\"" ws ":" ws integer ws "," ws "\"chunk_id\"" ws ":" ws integer ws "," ws "\"entities\"" ws ":" ws entity-array ws "," ws "\"uncertain_items\"" ws ":" ws string-array ws "}" ws

entity-array ::= "[" ws (entity ("," ws entity){0,19})? "]" ws

entity ::= "{" ws
  "\"name\"" ws ":" ws string ws "," ws
  "\"type\"" ws ":" ws entity-type ws "," ws
  "\"aliases\"" ws ":" ws string-array ws "," ws
  "\"description\"" ws ":" ws string ws "," ws
  "\"evidence_text\"" ws ":" ws string ws "," ws
  "\"confidence\"" ws ":" ws confidence ws "," ws
  "\"uncertain\"" ws ":" ws boolean ws
"}" ws

entity-type ::= "\"CHARACTER\"" | "\"LOCATION\"" | "\"ITEM\"" | "\"ORG\"" | "\"TITLE\"" | "\"UNKNOWN\""

string-array ::= "[" ws (string ("," ws string){0,9})? "]" ws

confidence ::= "0" ("." [0-9]{1,2})? | "1" (".0" "0"?)?
boolean ::= "true" | "false"
integer ::= [0-9]+

string ::= "\"" char* "\"" ws
char ::= [^"\\\x7F\x00-\x1F] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F]{4})
ws ::= [ \t\n]{0,20}
```

### 7.5 Prompt 与 GBNF 的配合

Prompt 不要写：“请输出 JSON”。

Prompt 应该写清楚：

```text
你是小说知识抽取器。
你只能基于给定片段抽取。
不要根据常识、影视改编、百科知识补充。
实体必须在原文中出现。
证据必须是原文中的连续短句。
如果不确定，uncertain=true。
如果没有实体，entities 输出空数组。
```

示例：

```text
任务：从小说片段中抽取实体候选。

规则：
1. 只抽取当前片段中明确出现的实体。
2. 不要根据你对整本书的记忆补充信息。
3. aliases 只填写片段中出现的别名或称呼。
4. evidence_text 必须是原文中能支持该实体存在的短句。
5. confidence 范围为 0 到 1。
6. 不确定时 uncertain=true。
7. 没有结果时 entities=[]。

输入：
book_title: {book_title}
chapter_id: {chapter_id}
chapter_title: {chapter_title}
chunk_id: {chunk_id}
text:
{chunk_text}
```

---

## 8. 抽取校验与重试机制

即使使用 GBNF，也必须保留后处理校验。

校验层级：

```text
1. JSON parse
2. JSON Schema / Pydantic validate
3. 字段值范围校验
4. evidence_text 是否出现在原文中
5. name/source/target 是否为空
6. confidence 是否为合法数值
7. relation source/target 是否在实体候选或上下文实体表中
8. 重复实体/关系去重
```

失败处理：

```text
FORMAT_ERROR：JSON 无法解析
SCHEMA_ERROR：字段不符合 schema
EVIDENCE_NOT_FOUND：证据不在原文中
EMPTY_REQUIRED_FIELD：关键字段为空
RELATION_ENTITY_MISSING：关系实体缺失
LOW_CONFIDENCE：置信度低于阈值
DUPLICATE：重复候选
```

重试策略：

```text
第一次失败：同 Prompt + 更低 temperature + 同 grammar 重试
第二次失败：改用更小任务 Prompt，例如只抽实体名
第三次失败：标记为 NEED_MANUAL_REVIEW，不再无限重试
```

---

## 9. 人工审核 UI 第一版

Demo 5 的人工审核 UI 不要做复杂。

第一版只需要完成：

### 9.1 候选实体审核页

左侧：原文 chunk  
右侧：候选实体列表

每个候选实体支持：

```text
通过
拒绝
修改名称
修改类型
修改别名
修改证据
标记不确定
```

### 9.2 候选关系审核页

左侧：原文证据  
中间：source - relation - target  
右侧：操作按钮

支持：

```text
通过
拒绝
修改关系类型
调换方向
修改证据
标记不确定
```

### 9.3 审核记录

每次人工修改都保存：

```text
candidate_id
old_value
new_value
review_action
reviewer
reviewed_at
comment
```

这些记录未来就是微调数据的核心来源。

---

## 10. 在线 QA 流程

Demo 5 的 QA 不追求复杂智能体，先做稳定闭环。

```text
用户问题
  → query rewrite，可选
  → BM25 检索 chunk
  → 向量检索 chunk
  → 合并候选 chunk
  → 识别问题中的实体名/别名
  → Neo4j 图谱扩展
  → 构造 QA context
  → llama.cpp 生成答案
  → 输出答案 + 引用 + 不确定说明
```

QA 输出格式：

```json
{
  "answer": "...",
  "citations": [
    {
      "chapter_id": 1,
      "chunk_id": 10,
      "excerpt": "..."
    }
  ],
  "unsupported_claims": [],
  "uncertainty": "..."
}
```

QA 原则：

1. 没有证据就不回答。
2. 不能用模型记忆替代书内证据。
3. 引用必须来自检索片段。
4. 图谱只用于组织上下文，最终回答仍要落到原文证据。
5. 如果图谱和原文冲突，以原文证据和审核状态为准。

---

## 11. Demo 5 不做什么

Demo 5 暂时不做：

```text
不做 QLoRA 微调
不做多用户高并发
不做复杂权限系统
不做完整 EPUB 复杂版式解析
不做外部 wiki 自动污染书内图谱
不做自动生成超大规模知识图谱
不做复杂 Agent 多轮规划
不做模型排行榜
不做过度精美前端
```

这些放到 Demo 6/7。

---

## 12. Demo 6 规划

Demo 6 主题：从实体抽取扩展到关系/事件/Claim，并增强图谱与审核闭环。

重点：

```text
1. 完善 GBNF 模板库：entity/event/relation/claim
2. 增加实体合并与别名管理
3. 增加关系抽取与方向审核
4. 增加事件抽取与参与者审核
5. 增加 Claim/证据抽取
6. 增加跨章节关系跟踪
7. 增加冲突检测
8. 增加抽取质量评估集
9. 增加审核效率工具
10. 增加小模型抽取对比
11. 打磨开源版 examples
```

Demo 6 应该开始正式服务开源社区目标。

建议新增目录：

```text
examples/
  journey_to_the_west_small/
  modern_chinese_novel_sample/
  english_novel_sample/

grammars/
  entity_extract.gbnf
  event_extract.gbnf
  relation_extract.gbnf
  claim_extract.gbnf
  qa_citation.gbnf

prompts/
  zh_entity_extract_v0.1.md
  zh_relation_extract_v0.1.md
  en_entity_extract_v0.1.md

benchmarks/
  extraction_eval_100.jsonl
  low_vram_report.md
```

---

## 13. Demo 7 规划

Demo 7 主题：GraphRAG QA、评测与基于 gold data 的行为微调准备。

目标：

```text
先实现稳定的带 citation GraphRAG QA，再用人工审核后的数据准备 Qwen3-14B 行为微调。
```

Demo 7 P0：

```text
1. BM25 + vector hybrid retrieval
2. Neo4j graph expansion
3. QA context builder
4. qa_citation GBNF / JSON Schema
5. answer + citations + unsupported_claims 输出
6. QA 失败和拒答记录
7. QA 样本导出为后续 SFT/QLoRA 数据
```

微调不是为了记住某本书，而是为了学会：

```text
基于上下文回答
必须引用
不确定时说明
证据不足时拒答
不要编造关系
结构化输出
```

数据来源：

```text
人工审核通过的实体抽取样本
人工审核通过的关系抽取样本
人工修正过的错误样本
带引用 QA 样本
拒答样本
别名/冲突/歧义样本
```

最低数据目标：

```text
500-1000 条抽取样本
300-500 条 QA 引用样本
50-100 条拒答样本
20-50 条别名/冲突样本
```

更理想目标：

```text
几千条高质量审核样本
```

---

## 14. 开源社区复用目标

你的第二个需求应该正式写入项目愿景。

NovelBridge 不只是个人项目，也可以沉淀为：

> 一套让普通开发者使用本地小模型完成小说结构化抽取和 GraphRAG 的工程模板。

目标用户：

```text
只有单张 RTX 3090 的开发者
只有 16GB/12GB 显存的开发者
只能跑 Qwen3-14B INT4 的开发者
只能跑 7B/8B 小模型的开发者
希望本地处理小说/文档但不想使用 API 的开发者
```

开源输出物：

```text
1. 可复用 Prompt 模板
2. 可复用 GBNF 规则
3. 低显存模型配置说明
4. 小规模样例小说数据
5. 抽取质量评估脚本
6. llama.cpp 启动脚本
7. JSON 校验与重试脚本
8. Neo4j 写入示例
9. GraphRAG QA 示例
10. 常见失败案例与修复方法
```

开源版不要一开始追求完整系统，而是先提供：

```text
book_extract_minimal/
  README.md
  run_llama_cpp.sh
  extract_entities.py
  extract_relations.py
  prompts/
  grammars/
  schemas/
  sample_book/
  outputs/
```

---

## 15. 低配模型适配策略

为了帮助单卡 3090 或更低配用户，抽取方案必须考虑小模型。

### 15.1 任务拆分

低配模型不适合一次抽全部内容。

应该拆为：

```text
Step 1：只抽实体名和类型
Step 2：基于实体表抽关系
Step 3：基于关系抽 evidence
Step 4：基于 evidence 生成 Claim
```

### 15.2 缩短上下文

小模型输入不要太长。

建议：

```text
每次输入 800-1200 中文字
附带上一 chunk 的实体摘要
不要塞整章
不要塞大段人物设定
```

### 15.3 固定输出字段

小模型输出字段越自由越容易崩。

必须固定字段、固定枚举、固定数组上限。

### 15.4 使用双层校验

```text
GBNF 保证格式
Pydantic/JSON Schema 保证字段
规则校验证据是否存在
人工审核保证事实正确
```

### 15.5 开源 Benchmark

至少提供三组模型测试：

```text
Qwen3-14B Q4_K_M
Qwen3-8B Q4_K_M
一个更低配 7B/8B 模型
```

指标：

```text
JSON parse success rate
schema valid rate
evidence hit rate
entity precision
relation precision
manual correction rate
tokens/sec
VRAM usage
```

---

## 16. 开发任务拆解

### 16.1 后端任务

```text
1. 新增 novel_chunk 表
2. 新增 novel_model_run 表
3. 新增 novel_extraction_candidate 表
4. 新增 novel_review_record 表
5. 新增 grammar_template / prompt_template 管理
6. 增加 extraction_run 状态机
7. 增加 Neo4j 写入服务
8. 增加 QA citation 保存
```

### 16.2 rag-agent 任务

```text
1. llama.cpp client
2. Prompt renderer
3. grammar/schema loader
4. extraction runner
5. JSON parser
6. schema validator
7. evidence validator
8. retry controller
9. result normalizer
10. MySQL/HTTP 回传接口
```

### 16.3 前端任务

```text
1. 书籍导入页面
2. 章节/分块查看页面
3. 抽取任务进度页面
4. 实体审核页面
5. 关系审核页面
6. 图谱预览页面
7. 带引用 QA 页面
```

### 16.4 图谱任务

```text
1. Neo4j Docker 配置
2. Book/Chapter/Chunk 节点写入
3. Entity/Event/Claim 节点写入
4. APPEARS_IN/SUPPORTED_BY/RELATED_TO 等关系写入
5. alias 合并策略
6. 查询接口
```

---

## 17. Demo 5 验收标准

Demo 5 可以认为完成的标准：

```text
1. 能导入一本中等长度小说样例
2. 能自动切分章节和 chunk
3. 能通过 llama.cpp 调用本地模型
4. 能使用 GBNF/JSON Schema 生成合法结构化 JSON
5. 能保存每次模型调用记录
6. 能生成实体候选
7. 能在前端审核实体候选结果
8. 审核通过的实体数据能写入 Neo4j
9. 抽取失败能被记录和复现
10. Prompt 和 GBNF 有版本号
11. 远程 Linux 一键启动脚本能拉起 Demo 5 所需服务
12. Spring Boot 能通过配置调用远程 rag-agent
```

最低技术指标：

```text
JSON parse success rate ≥ 95%
Schema valid rate ≥ 90%
Evidence hit rate ≥ 80%
人工审核后入图数据可追溯率 = 100%
远程服务 health check 全部通过
```

---

## 18. 建议项目目录

```text
novelbridge-agents/
  backend/
    spring-boot-app/
  rag-agent/
    app/
      clients/
        llama_cpp_client.py
      prompts/
      grammars/
      schemas/
      runners/
      validators/
      normalizers/
    tests/
  frontend/
  docker/
    neo4j/
    mysql/
  examples/
    sample_book/
  docs/
    demo5_requirements.md
    gbnf_design.md
    extraction_schema.md
    open_source_low_vram_guide.md
```

---

## 19. 需求问答版澄清

### Q1：Demo 5 是先做 QA，还是先做抽取？

先做抽取。没有稳定实体、关系、Claim 和引用证据，QA 只是表面效果。

### Q2：GBNF 是不是能彻底解决抽取质量问题？

不能。GBNF 主要解决格式问题，不解决事实问题。事实问题靠 Prompt、证据校验、图谱约束和人工审核。

### Q3：是否需要一开始就微调 Qwen3-14B？

不需要。先用 Demo 5 收集人工审核数据，否则微调缺少高质量样本。

### Q4：Neo4j 是否必须现在上？

Demo 5 应该上最小 Neo4j。因为你的目标是 GraphRAG，不应该继续只在 MySQL 中模拟关系。

### Q5：是否需要外部 wiki？

Demo 5 不需要。外部 wiki 可以在 Demo 6 作为单独 external graph，不允许自动污染书内 canon。

### Q6：单卡 3090 用户能不能复用？

可以，但要依赖任务拆分、短上下文、GBNF、固定 schema、强校验和人工审核。

### Q7：小模型能不能做小说抽取？

可以做，但不要让它一次完成复杂任务。小模型适合“短片段 + 单任务 + 固定格式 + 强校验”的工程路线。

### Q8：Prompt 和 GBNF 谁更重要？

两者都重要。Prompt 解决“抽什么、怎么判断”，GBNF 解决“输出必须长什么样”。

### Q9：Demo 5 最应该避免什么？

避免一次性做太大：复杂前端、复杂 Agent、复杂 wiki、复杂微调都应该推后。

### Q10：最值得沉淀给开源社区的是什么？

不是完整系统，而是“低配本地模型也能稳定抽取小说结构化知识”的 Prompt + GBNF + 校验 + 示例工程。

---

## 20. 下一步最小开发顺序

建议拆成 Demo 5/6/7 推进，不要把完整 GraphRAG 一次塞进 Demo 5。

### Demo 5A：远程服务底座

```text
第 1 步：建立 deploy/remote 和 scripts/remote 目录
第 2 步：编写 .env.example / ports.env / services.yaml
第 3 步：编写 nb_up.sh / nb_down.sh / nb_status.sh / nb_healthcheck.sh
第 4 步：编写 Windows PowerShell SSH 包装脚本
第 5 步：拉起 MySQL / Neo4j / Vector DB 最小服务
第 6 步：拉起 llama.cpp OpenAI-compatible endpoint
第 7 步：建立 rag-agent /health
第 8 步：Spring Boot 配置 rag-agent base-url
```

### Demo 5B：Chunk + ModelRun + Entity Candidate

```text
第 1 步：新增 novel_chunk / novel_model_run / candidate / review 表
第 2 步：生成 chapter -> chunk
第 3 步：实现 entity_extract Prompt + JSON Schema
第 4 步：接入 llama.cpp response_format / json_schema 或 grammar
第 5 步：实现 JSON parse、Schema validate、evidence validate
第 6 步：保存 raw prompt / raw output / parse error 到 novel_model_run
第 7 步：生成实体候选并进入 review queue
第 8 步：实现最小实体审核页面
第 9 步：审核通过后写入 Neo4j 最小图谱
第 10 步：沉淀 entity prompt / schema / grammar / sample outputs
```

### Demo 6：关系、事件、Claim 与图谱增强

```text
第 1 步：实现 relation_extract
第 2 步：实现 event_extract
第 3 步：实现 claim_extract
第 4 步：实现关系/事件/Claim 审核页面
第 5 步：实现实体合并和别名管理
第 6 步：实现 Neo4j 关系写入和冲突检测
第 7 步：建立 extraction benchmark
第 8 步：沉淀开源版 prompts、grammars、schemas、examples
```

### Demo 7：GraphRAG QA 与微调数据准备

```text
第 1 步：实现 vector/BM25 检索
第 2 步：实现 graph expansion
第 3 步：实现 QA context builder
第 4 步：实现 qa_citation schema/grammar
第 5 步：实现带 citation 的 QA
第 6 步：记录 QA 失败、拒答、人工修正
第 7 步：导出 SFT/QLoRA 训练样本
```

---

## 21. Demo 5 优先级排序

### P0：必须完成

```text
远程 Linux 服务底座
一键启动脚本和 health check
chunk 生成
llama.cpp 调用
GBNF/JSON Schema 约束输出
model_run 记录
entity candidate 记录
实体人工审核
Neo4j 最小 Entity/Chunk/Chapter 写入
Spring Boot 调用 rag-agent
```

### P1：应尽量完成

```text
Prompt/Grammar 版本管理
实体别名管理
证据文本高亮
抽取失败分类
抽取质量统计
低配模型运行说明
```

### P2：可以推后

```text
关系/事件/Claim 抽取
带引用 QA 最小闭环
复杂图谱可视化
外部 wiki 对齐
多模型评测平台
QLoRA 微调
多用户权限
高并发服务
复杂 Agent 工作流
```

---

## 22. 最终结论

Demo 5 的核心不是“问答效果看起来不错”，而是完成一个可靠工程闭环。

```text
本地模型 + GBNF/JSON Schema 结构化输出 + 候选数据入库 + 人工审核 + Neo4j 图谱写入 + 原文证据引用 + GraphRAG 问答
```

你的两个新增需求应直接进入核心设计。

第一，GBNF 用于在采样层约束结构化输出，是 Demo 5 的 P0 能力。  
第二，Neo4j、向量库、MySQL、llama.cpp 和 Python `rag-agent` 应统一部署在远程 Linux 服务器上，本地 Windows 主要运行 Java 后端开发、前端展示和调试入口。

---

## 23. 当前项目进度对齐

结合当前代码和文档状态，Demo 5 不是从零开始。

当前已经具备：

```text
1. Spring Boot 后端骨架
2. Book / Chapter 导入与章节切分
3. AgentRun / AgentStep 长任务追踪
4. ChatSession / ChatMessage / Citation 最小问答数据链路
5. 静态工作台页面
6. 基于关键词的 mock QA
```

当前仍然是 mock/debt 的部分：

```text
1. ChapterSplitter 仍是 Java 正则规则，尚未接 Python splitter
2. 尚未生成 novel_chunk
3. 尚未持久化 novel_model_run
4. QA 仍是关键词检索和模板回答
5. 尚未接 llama.cpp
6. 尚未接 Neo4j / 向量库 / BM25 混合检索
7. 尚未有人审候选数据闭环
```

因此 Demo 5 的实际开发重点不是重做 Demo 1-4，而是替换关键 mock：

```text
Book/Chapter 已有
  -> 新增 Chunk
  -> 新增 ModelRun
  -> 新增 ExtractionCandidate / ReviewRecord
  -> 接入远程 rag-agent
  -> 接入远程 llama.cpp
  -> 接入远程 MySQL / Neo4j / Vector DB
  -> 前端增加最小审核 UI
  -> QA 从 keyword mock 升级为 GraphRAG + Citation
```

---

## 24. 远程 Linux 部署规划

### 24.1 部署原则

模型、数据和检索服务统一放在远程 Linux 服务器上：

```text
llama.cpp / llama-server
Python rag-agent
MySQL
Neo4j
Vector DB
BM25/Search service
```

本地 Windows 机器保留：

```text
Java/Spring Boot 开发
前端展示和调试
Reasonix/OpenCode agent 开发流程
SSH 远程管理脚本
```

不要把服务器密码写入仓库、文档、脚本或 `.env.example`。仓库中只允许出现：

```text
NB_REMOTE_HOST=192.168.3.50
NB_REMOTE_PORT=22
NB_REMOTE_USER=wk
```

密码、私钥路径、数据库密码、Neo4j 密码、服务 token 必须放在本机未提交的 `.env` 或系统凭据管理器中。

### 24.2 推荐服务拓扑

```text
Windows 本地
  ├─ Spring Boot backend: http://localhost:8080
  ├─ Frontend/static workbench: http://localhost:8080 或独立 dev server
  └─ SSH tunnel / HTTP client

Linux 服务器 192.168.3.50
  ├─ llama-server: 127.0.0.1:18080
  ├─ rag-agent: 0.0.0.0:18081
  ├─ MySQL: 127.0.0.1:13306 或 Docker network 内部 3306
  ├─ Neo4j HTTP/Bolt: 17474 / 17687
  ├─ Vector DB: 16333 或 18082
  └─ Search/BM25: 18083，可后置
```

外部暴露建议：

```text
只暴露 rag-agent 给本地 Java 后端调用。
MySQL / Neo4j / llama-server 默认只绑定 127.0.0.1 或 Docker 内网。
本地开发通过 SSH tunnel 访问内部端口。
```

### 24.3 端口约定

| 服务 | 推荐端口 | 暴露范围 | 说明 |
|---|---:|---|---|
| `llama-server` | `18080` | Linux localhost | OpenAI-compatible API |
| `rag-agent` | `18081` | LAN 或 SSH tunnel | Spring Boot 调用入口 |
| `mysql` | `13306` | Linux localhost / tunnel | 避免和系统 MySQL 冲突 |
| `neo4j-http` | `17474` | Linux localhost / tunnel | Neo4j Browser/API |
| `neo4j-bolt` | `17687` | Linux localhost / tunnel | Driver 连接 |
| `vector-db` | `16333` | Linux localhost / tunnel | Qdrant/Chroma 二选一 |
| `search` | `18083` | Linux localhost | BM25，可后置 |

端口必须由统一配置文件管理，不允许散落在代码里。

建议配置文件：

```text
deploy/remote/.env.example
deploy/remote/ports.env
deploy/remote/services.yaml
```

---

## 25. 一键启动脚本规划

### 25.1 目标

需要一个脚本完成：

```text
1. 检查远程服务器连接
2. 检查 GPU / CUDA / llama.cpp 可执行文件
3. 检查模型文件路径
4. 检查 Docker / Python venv
5. 自动选择或校验端口
6. 启动 MySQL / Neo4j / Vector DB
7. 启动 llama-server
8. 启动 rag-agent
9. 执行 health check
10. 输出本地 Spring Boot 应该使用的 endpoint
```

### 25.2 脚本分层

Windows 本地入口：

```text
scripts/remote/nb_remote_up.ps1
scripts/remote/nb_remote_down.ps1
scripts/remote/nb_remote_status.ps1
scripts/remote/nb_tunnel_up.ps1
```

Linux 服务器入口：

```text
deploy/remote/nb_up.sh
deploy/remote/nb_down.sh
deploy/remote/nb_status.sh
deploy/remote/nb_healthcheck.sh
deploy/remote/nb_ports.py
```

建议由本地 PowerShell 调 SSH 调用远程脚本：

```powershell
ssh -p $env:NB_REMOTE_PORT "$env:NB_REMOTE_USER@$env:NB_REMOTE_HOST" "cd ~/novelbridge-deploy && bash deploy/remote/nb_up.sh"
```

### 25.3 端口自动配置

端口选择策略：

```text
1. 优先使用 ports.env 中固定端口
2. 如果端口占用，脚本报错并给出占用进程
3. Demo 阶段不建议自动随机改端口
4. 如必须自动改端口，必须回写 runtime-ports.env，并输出给 Spring Boot
```

原因：

```text
自动随机端口会让 Spring Boot、rag-agent、health check、文档和调试命令变复杂。
Demo 5 更适合固定端口 + 明确失败。
```

### 25.4 推荐 health check

```text
GET http://127.0.0.1:18081/health
GET http://127.0.0.1:18081/health/llm
GET http://127.0.0.1:18081/health/mysql
GET http://127.0.0.1:18081/health/neo4j
GET http://127.0.0.1:18081/health/vector
```

`rag-agent` 的健康检查应返回：

```json
{
  "status": "UP",
  "llama_cpp": "UP",
  "mysql": "UP",
  "neo4j": "UP",
  "vector": "UP",
  "model": "Qwen3.6-35B-A3B",
  "grammar_enabled": true
}
```

---

## 26. Python rag-agent 工作流约束

`rag-agent` 是 Demo 5 的模型与检索编排层，不是另一个自由发挥的业务系统。

### 26.1 rag-agent 职责

```text
1. 调用 llama.cpp OpenAI-compatible API
2. 管理 Prompt / GBNF / JSON Schema
3. 执行抽取任务
4. 做 JSON parse / schema validate / evidence validate
5. 做失败重试和错误分类
6. 写入或回传 model_run / candidate / review 数据
7. 调用 Neo4j 和向量库
8. 为 Spring Boot 提供统一 API
```

### 26.2 rag-agent 不负责

```text
1. 不负责用户权限
2. 不直接替代 Spring Boot 的业务接口
3. 不绕过 AgentRun / AgentStep
4. 不直接把未审核候选写成最终图谱真相
5. 不隐藏原始 prompt/output/error
```

### 26.3 API 草案

Demo 5 必做：

```text
GET  /health
GET  /health/llm
GET  /health/mysql
GET  /health/neo4j
GET  /health/vector
POST /extract/entities
POST /review/apply-entities-to-graph
POST /admin/reload-prompts
POST /admin/reload-grammars
```

Demo 6/7 预留：

```text
POST /extract/events
POST /extract/relations
POST /extract/claims
POST /qa/answer
```

### 26.4 状态与审计约束

每次 `rag-agent` 调用模型必须产生一条 `novel_model_run` 或等价记录：

```text
run_id
step_id
task_type
model_name
model_endpoint
prompt_version
grammar_version
input_ref 或 input_text
raw_output_ref 或 raw_output_text
parse_status
error_type
retry_count
duration_ms
created_at
```

如果模型输出被修复、重试或人工修改，必须保留原始版本，不允许覆盖。

---

## 27. Spring Boot 调用方案：Spring AI 还是 LangChain4j

### 27.1 当前结论

Demo 5 推荐：

```text
Spring Boot 不直接承担复杂 LLM/RAG 编排。
Java 后端优先通过普通 HTTP client 调用 Python rag-agent。
如后续要在 Java 层引入 AI SDK，优先考虑 Spring AI。
```

原因：

```text
1. 当前复杂逻辑在 Python 更适合：GBNF、Pydantic、Neo4j、向量库、脚本化部署。
2. Java 后端已有 AgentRun/AgentStep/Citation，应该保持业务编排和审计清晰。
3. rag-agent 已经提供 OpenAI-compatible/REST 边界，Java 层不需要过早绑定 AI 框架。
```

### 27.2 Spring AI 的适配点

Spring AI 更适合：

```text
1. Spring Boot 原生配置
2. ChatClient 风格调用
3. OpenAI-compatible base-url
4. 与 Spring Boot Actuator/Observability 结合
5. 后续需要在 Java 内部做轻量 chat/embedding 调用
```

官方文档显示 Spring AI 提供 `ChatClient`、OpenAI/OpenAI SDK 适配、base-url 配置、Vector Store API 和观测能力。Demo 5 如果 Java 侧只是调用 llama.cpp 或 rag-agent 的 OpenAI-compatible endpoint，Spring AI 是更自然的 Spring 生态选择。

### 27.3 LangChain4j 的适配点

LangChain4j 更适合：

```text
1. Java 内部直接做 Agent/RAG/工具调用
2. 想要更完整的 Java LLM 抽象层
3. 不想引入 Python rag-agent
4. 需要在 Java 里快速组合 embedding、memory、retriever、tools
```

但本项目 Demo 5 已经决定使用 Python `rag-agent` 承担模型和 GraphRAG 编排，所以 LangChain4j 的高级抽象暂时不是必需。

### 27.4 推荐落地方式

Demo 5：

```text
Spring Boot -> WebClient/RestClient -> rag-agent REST API
rag-agent -> llama.cpp / MySQL / Neo4j / Vector DB
```

Demo 6/7 后再评估：

```text
如果 Java 层只需要简单调用：继续 RestClient 或 Spring AI。
如果 Java 层要自己编排 Agent/RAG：再比较 LangChain4j。
```

当前不要同时引入 Spring AI、LangChain4j 和 Python LangChain/LangGraph。框架过多会让问题定位困难。

---

## 28. 部署与开发优先级补充

### P0 新增

```text
远程 Linux deploy 目录
远程 .env.example，不包含密码
固定端口 ports.env
nb_up.sh / nb_down.sh / nb_status.sh / nb_healthcheck.sh
Windows PowerShell SSH 包装脚本
rag-agent /health
Spring Boot 配置 rag-agent base-url
```

### P1 新增

```text
SSH tunnel 脚本
服务日志目录和 log rotate
模型文件 checksum 检查
端口占用诊断
GPU 显存检查
一键 smoke test：抽取一个 sample chunk
```

### P2 新增

```text
systemd service
Docker Compose GPU profile
多模型切换
自动下载模型
远程 Web 管理页面
```
