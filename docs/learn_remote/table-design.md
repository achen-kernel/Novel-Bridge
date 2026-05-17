# NovelBridge-Agents 数据表设计 v1

> 设计日期：2026-05-13
> 数据库：MySQL 8.0 / 库名 `novel_bridge`
> 字符集：utf8mb4
> 统一前缀：`novel_`

---

## 一、设计原则

### 1. 统一字段

所有表都包含以下基础字段（由 Java 父类 `BaseEntity` 自动生成）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | BIGINT (PK, AUTO_INCREMENT) | 主键 |
| `created_at` | DATETIME | 创建时间（自动） |
| `updated_at` | DATETIME | 最后修改时间（自动） |
| `created_by` | VARCHAR(50) | 创建人 |
| `updated_by` | VARCHAR(50) | 最后修改人 |

### 2. 状态与错误追踪

模型产物、长任务、审核对象额外包含：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | VARCHAR(20) | 状态枚举值 |
| `error_message` | TEXT | 失败原因（NULL 表示正常） |

### 3. 数据库设计决策

- **单一数据库** `novel_bridge`，所有表通过 `book_id` 或 `project_id` 归属
- 不采用"一书一库"，避免连接管理复杂化
- 重要度通过 `significance` 枚举区分（MAJOR / SUPPORTING / MINOR / CAMEO）
- 所有 AI 产物默认 `status = 'AUTO_EXTRACTED'`，不作为权威知识

---

## 二、表清单速览（20 张）

| # | 表名 | 分类 | 核心作用 |
| --- | --- | --- | --- |
| 1 | novel_user | 业务 | 系统用户 |
| 2 | novel_project | 业务 | 项目，可包含多本书 |
| 3 | novel_folder | 业务 | 项目内的文件夹/分类 |
| 4 | novel_book | 核心 | 书籍元数据 |
| 5 | novel_chapter | 核心 | 章节（按章/卷/篇） |
| 6 | novel_chunk | 核心 | 文本片段，构建索引的最小单位 |
| 7 | novel_chapter_fact | 核心 | 从章节抽取的事实 |
| 8 | novel_entity_profile | 核心 | 实体画像（人物/地点/物品注册） |
| 9 | novel_agent_run | 追踪 | 一次长任务运行 |
| 10 | novel_agent_step | 追踪 | 长任务中的一个步骤 |
| 11 | novel_model_run | 追踪 | 一次模型调用记录 |
| 12 | novel_chat_session | 问答 | 一次对话会话 |
| 13 | novel_chat_message | 问答 | 对话中的单条消息 |
| 14 | novel_chat_question_index | 问答 | 问题索引（供快速检索） |
| 15 | novel_citation | 问答 | 回答的证据引用 |
| 16 | novel_review_item | 预留 | 人工审核条目 |
| 17 | novel_eval_case | 预留 | 评测用例 |
| 18 | novel_eval_result | 预留 | 评测结果 |
| 19 | novel_prompt_version | 预留 | Prompt 版本管理 |
| 20 | novel_retriever_version | 预留 | 检索策略版本管理 |

---

## 三、表详述

---

### 1. novel_user — 用户

最基础的账户表。v1 暂不涉及权限和登录校验，先存用户信息。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 登录名 |
| password | VARCHAR(255) | NOT NULL | 密码（v1 明文，后续加密） |
| display_name | VARCHAR(100) | | 显示名 |
| email | VARCHAR(100) | | 邮箱 |
| avatar | VARCHAR(255) | | 头像 URL |
| enabled | BOOLEAN | default true | 是否启用 |

---

### 2. novel_project — 项目

一个项目可以包含多本书（例如"中国神话研究"项目下包含《山海经》《搜神记》《聊斋志异》）。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| name | VARCHAR(100) | NOT NULL | 项目名称 |
| description | TEXT | | 项目描述 |
| owner_id | BIGINT | FK → novel_user.id | 项目所有者 |
| status | VARCHAR(20) | default 'ACTIVE' | ACTIVE / ARCHIVED |

---

### 3. novel_folder — 文件夹

项目内的分层组织，例如"神兽/植物/矿物"分类。支持父文件夹实现树形结构。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| name | VARCHAR(100) | NOT NULL | 文件夹名 |
| project_id | BIGINT | FK → novel_project.id | 所属项目 |
| parent_id | BIGINT | FK → novel_folder.id, nullable | 父文件夹（树形） |
| sort_order | INT | default 0 | 排序 |

**学习点**：`parent_id` 自引用实现无限层级，这是树形结构的经典做法。

---

### 4. novel_book — 书籍

一本书的核心元数据。从上传 txt/md 文件开始。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| project_id | BIGINT | FK → novel_project.id | 所属项目 |
| folder_id | BIGINT | FK → novel_folder.id, nullable | 所在文件夹 |
| title | VARCHAR(255) | NOT NULL | 书名 |
| author | VARCHAR(100) | | 作者 |
| source_filename | VARCHAR(255) | NOT NULL | 原始上传文件名 |
| source_path | VARCHAR(500) | NOT NULL | **服务端路径，不返回前端** |
| file_size | BIGINT | | 文件字节数 |
| file_type | VARCHAR(10) | | txt / md |
| total_chapters | INT | default 0 | 总章节数 |
| total_chunks | INT | default 0 | 总 chunk 数 |
| status | VARCHAR(20) | default 'IMPORTED' | 见下方状态流转 |
| error_message | TEXT | | 构建失败时的原因 |

**BookStatus 流转**：
```
IMPORTED → BUILDING → READY_FOR_QA
                            ↓
                     BUILD_FAILED（失败时）
```

---

### 5. novel_chapter — 章节

一本书的内容划分单元。不同书籍类型映射方式不同：

| 书籍类型 | 章节映射方式 |
| --- | --- |
| 主线小说 | 第1章、第2章... |
| 《山海经》 | 南山经、西山经、北山经... |
| 《聊斋志异》 | 卷1、卷2...（每卷内多个故事用 chunk 区分） |

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| book_id | BIGINT | FK → novel_book.id, INDEX | 所属书 |
| chapter_number | INT | NOT NULL | 章节序号 |
| title | VARCHAR(500) | | 章节标题 |
| raw_content | LONGTEXT | | 原始文本 |
| cleaned_content | LONGTEXT | | 清洗后文本 |
| char_count | INT | default 0 | 字符数 |
| status | VARCHAR(20) | default 'CREATED' | CREATED / CLEANED / FACT_EXTRACTED |
| error_message | TEXT | | |

**联合唯一索引**：`(book_id, chapter_number)`

---

### 6. novel_chunk — 文本片段

Chunk 是构建索引和检索的最小单位。一篇文章按固定大小（如 512 tokens）切分成多个 chunk，重叠部分确保上下文不丢失。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| chapter_id | BIGINT | FK → novel_chapter.id, INDEX | 所属章节 |
| book_id | BIGINT | FK → novel_book.id, INDEX | 所属书 |
| chunk_index | INT | NOT NULL | 在章节内的序号 |
| content | LONGTEXT | NOT NULL | 文本内容 |
| char_count | INT | default 0 | 字符数 |
| embedding_id | VARCHAR(100) | | Chroma 向量 ID（v2 用） |

**为什么需要 Chunk**：模型不能一次读整本书，需要切成小片才能检索和引用。

---

### 7. novel_chapter_fact — 章节事实

模型从每一章抽取的事实。这是模型产物的**原始记录层**，默认 `AUTO_EXTRACTED`，不直接作为权威知识。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| chapter_id | BIGINT | FK → novel_chapter.id, INDEX | 所属章节 |
| book_id | BIGINT | FK → novel_book.id, INDEX | 所属书 |
| fact_type | VARCHAR(50) | | CHARACTER / EVENT / LOCATION / ITEM / RELATIONSHIP |
| fact_content | TEXT | NOT NULL | 事实内容 |
| confidence | DOUBLE | default 1.0 | 模型置信度 |
| status | VARCHAR(20) | default 'AUTO_EXTRACTED' | DRAFT / AUTO_EXTRACTED / APPROVED / REJECTED |
| error_message | TEXT | | |

**示例**：
```
fact_type = 'CHARACTER'
fact_content = '九尾狐，青丘之山有兽焉，其状如狐而九尾'
```

---

### 8. novel_entity_profile — 实体画像

这是你特别关注的表。它跨章节聚合同一个人物/地点/物品的完整信息。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| book_id | BIGINT | FK → novel_book.id | 所属书 |
| entity_name | VARCHAR(200) | NOT NULL | 实体名称 |
| entity_type | VARCHAR(50) | | CHARACTER / LOCATION / ITEM / EVENT |
| aliases | TEXT | | 别名集合（JSON 或逗号分隔） |
| description | TEXT | | 综合描述 |
| **significance** | VARCHAR(20) | default 'MINOR' | **重要度** |
| first_chapter_id | BIGINT | FK → novel_chapter.id | 首次出现章节 |
| last_chapter_id | BIGINT | FK → novel_chapter.id | 最后出现章节 |
| status | VARCHAR(20) | default 'AUTO_EXTRACTED' | |
| error_message | TEXT | | |

**Significance 枚举**：

| 级别 | 含义 | 示例 |
| --- | --- | --- |
| MAJOR | 主角 / 核心人物 | 宁采臣（聊斋）、孙悟空（西游） |
| SUPPORTING | 重要配角 | 燕赤霞（聊斋·聂小倩） |
| MINOR | 次要角色 | 只在某一篇出现的路人 |
| CAMEO | 仅提及 | 名字出现过一次 |

**v1 职责**：建表 + CRUD，不做跨章聚合逻辑。v2 才做跨章合并。

---

### 9. novel_agent_run — 长任务运行

每次需要多步骤完成的 AI 任务（如构建一本书）记录一条 `AgentRun`。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| run_type | VARCHAR(50) | NOT NULL | BOOK_BUILD / QUERY_ANSWER / REVIEW / EVAL |
| book_id | BIGINT | FK → novel_book.id, nullable | 关联书 |
| status | VARCHAR(20) | NOT NULL, default 'PENDING' | PENDING → RUNNING → SUCCESS/FAILED |
| started_at | DATETIME | | 开始时间 |
| completed_at | DATETIME | | 完成时间 |
| error_message | TEXT | | |

**TaskStatus**：`PENDING → RUNNING → SUCCESS / FAILED / CANCELED`

---

### 10. novel_agent_step — 任务步骤

`AgentRun` 内部的一个具体步骤，例如"清洗文本→切章节→切 chunk→建索引→抽取事实"。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| agent_run_id | BIGINT | FK → novel_agent_run.id, INDEX | 所属任务 |
| step_type | VARCHAR(50) | NOT NULL | CLEAN_TEXT / SPLIT_CHAPTERS / BUILD_CHUNKS / EXTRACT_FACT... |
| step_order | INT | NOT NULL | 步骤序号 |
| status | VARCHAR(20) | NOT NULL, default 'WAITING' | WAITING → RUNNING → SUCCESS/FAILED |
| started_at | DATETIME | | |
| completed_at | DATETIME | | |
| error_message | TEXT | | |

**StepStatus**：`WAITING → RUNNING → SUCCESS / FAILED / RETRYING / SKIPPED`

**学习点**：`AgentRun` 和 `AgentStep` 是一对多的经典主从关系。这是整个项目"可追踪"的地基。

---

### 11. novel_model_run — 模型调用记录

每次调用大模型的输入输出都记录在这里，用于复现问题、评估质量。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| agent_step_id | BIGINT | FK → novel_agent_step.id, nullable | 所属步骤 |
| model_name | VARCHAR(100) | NOT NULL | 模型名称（如 llama3-8b） |
| prompt_version | VARCHAR(50) | | Prompt 版本号 |
| input_tokens | INT | | 输入 token 数 |
| output_tokens | INT | | 输出 token 数 |
| input_text | LONGTEXT | | 发送给模型的完整 prompt |
| output_text | LONGTEXT | | 模型返回的完整回答 |
| duration_ms | BIGINT | | 耗时（毫秒） |
| status | VARCHAR(20) | default 'SUCCESS' | |
| error_message | TEXT | | |

---

### 12. novel_chat_session — 对话会话

用户针对某本书发起的一次问答会话。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| book_id | BIGINT | FK → novel_book.id | 针对哪本书提问 |
| user_id | BIGINT | FK → novel_user.id | 提问者 |
| title | VARCHAR(255) | | 会话标题 |
| status | VARCHAR(20) | default 'ACTIVE' | ACTIVE / CLOSED |

---

### 13. novel_chat_message — 聊天消息

一次会话中的单条消息，可能是用户问题或 AI 回答。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| session_id | BIGINT | FK → novel_chat_session.id, INDEX | 所属会话 |
| role | VARCHAR(20) | NOT NULL | USER / ASSISTANT / SYSTEM |
| content | LONGTEXT | NOT NULL | 消息内容 |
| message_index | INT | | 在会话中的序号 |

---

### 14. novel_chat_question_index — 问题索引

把用户的问题单独提取出来，方便后续快速查看"这本书被问过哪些问题"。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| session_id | BIGINT | FK → novel_chat_session.id | 所属会话 |
| message_id | BIGINT | FK → novel_chat_message.id | 对应的消息 |
| question_text | TEXT | NOT NULL | 问题文本 |
| is_active | BOOLEAN | default true | 是否有效 |

---

### 15. novel_citation — 引用

AI 回答中引用原文证据的记录。这是项目**可追溯**的核心。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| message_id | BIGINT | FK → novel_chat_message.id, INDEX | 被引用的消息 |
| source_type | VARCHAR(20) | NOT NULL | CHAPTER / CHUNK / FACT |
| source_id | BIGINT | NOT NULL | 引用来源的 ID |
| chapter_id | BIGINT | FK → novel_chapter.id | 冗余字段，方便按章节查 |
| chunk_id | BIGINT | FK → novel_chunk.id | |
| fact_id | BIGINT | FK → novel_chapter_fact.id | |
| relevance_score | DOUBLE | | 相关度分数 |
| excerpt | TEXT | | 被引用的具体文本 |

---

### 16 ~ 20. 预留表（v2 再完整实现）

这些表 v1 建轻量结构，不做复杂业务。

| # | 表名 | 预留用途 |
| --- | --- | --- |
| 16 | novel_review_item | 人工审核队列（把 AUTO_EXTRACTED 转 APPROVED / REJECTED） |
| 17 | novel_eval_case | 黄金问答集（预设问题和期望答案） |
| 18 | novel_eval_result | 评测结果（记录每次评测的精度和分数） |
| 19 | novel_prompt_version | Prompt 版本管理（版本化、对比） |
| 20 | novel_retriever_version | 检索策略版本管理 |

---

## 四、实体关系总图

```
User ──< Project              (owner)
User ──< ChatSession
User ──< ReviewItem           (reviewer)

Project ──< Folder
Project ──< Book

Folder ──< Folder             (parent, 自引用树形)

Book ──< Chapter
Book ──< Chunk
Book ──< ChapterFact
Book ──< EntityProfile        ← 你特别关注的表
Book ──< AgentRun
Book ──< ChatSession
Book ──< EvalCase

Chapter ──< Chunk
Chapter ──< ChapterFact
Chapter ──< EntityProfile     (first_chapter / last_chapter)

AgentRun ──< AgentStep
AgentStep ──< ModelRun

ChatSession ──< ChatMessage
ChatMessage ──< Citation
ChatMessage ──< ChatQuestionIndex

EvalCase ──< EvalResult
```

---

## 五、按轮次实现顺序

| 轮次 | 要建的表 | 原因 |
| --- | --- | --- |
| 第3轮 | 无（写 common/ 基础设施） | 先搭地基 |
| 第4轮 | 1~8（业务核心表） | 先有数据骨架 |
| 第5轮 | 9~15（追踪 + 问答表） | 再建任务和问答 |
| 第6~8轮 | 16~20（预留表） | 配套业务逻辑 |
