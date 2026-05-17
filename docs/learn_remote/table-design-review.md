# Table Design Review

参考来源：

- `docs/learn_remote/table-design.md`
- AI-reader 表设计思路（已吸收为本文件中的对比结论，原始长文不再保留）

## 结论

当前 20 表设计方向正确，但对第一个 demo 偏重。建议保留完整蓝图，同时把实现顺序改成：

```text
demo-core -> v1-core -> v1-hardening -> v2
```

AI-reader 的核心经验值得吸收：章节事实用 JSON 保存原始模型输出，角色档案优先从章节事实聚合，不要太早维护复杂预聚合表。

## 分层建议

| 层级 | 表 | 说明 |
|---|---|---|
| demo-core | `novel_book`, `novel_chapter`, `novel_chunk`, `novel_chapter_fact` | 书籍、章节、片段、章节事实 |
| demo-core | `novel_agent_run`, `novel_agent_step`, `novel_model_run` | 构建和问答过程追踪 |
| demo-core | `novel_chat_session`, `novel_chat_message`, `novel_citation` | 最小问答和引用 |
| v1-core | `novel_user`, `novel_project`, `novel_folder` | 真实多项目/多书管理 |
| v1-hardening | `novel_chat_question_index`, `novel_entity_profile`, `novel_prompt_version`, `novel_retriever_version` | 工作台体验、主要角色、版本管理 |
| v2 | `novel_review_item`, `novel_eval_case`, `novel_eval_result` | 审核和评测闭环 |

## 角色表建议

你想保留“主要角色做一个表”是合理的，但它不应该替代 `chapter_fact`。

推荐混合模型：

```text
chapter_facts.fact_json = 原始章节事实，保留每章 LLM 输出
entity_profile = 主要角色/地点/物品的聚合档案和人工修正入口
entity_dictionary = 可选，抽取前的轻量实体词典
```

`entity_profile` 的定位应是“可展示、可审核、可修正的聚合结果”，不是唯一事实来源。

建议字段：

| 字段 | 说明 |
|---|---|
| `book_id` | 所属书 |
| `entity_name` | 规范名 |
| `entity_type` | CHARACTER / LOCATION / ITEM / ORG / EVENT |
| `aliases_json` | 别名列表 |
| `profile_json` | 聚合后的角色档案，如经历、能力、关系、外貌 |
| `significance` | MAJOR / SUPPORTING / MINOR / CAMEO |
| `first_chapter_id` | 首次出现 |
| `last_chapter_id` | 最后出现 |
| `source_fact_ids_json` | 聚合来源 fact |
| `status` | AUTO_EXTRACTED / REVIEWING / APPROVED / REJECTED / NEED_FIX |
| `error_message` | 聚合失败或审核问题 |

Demo 阶段可以只建 `entity_profile` 的轻量版本：

```text
id, book_id, entity_name, entity_type, significance, status, profile_json
```

## 需要补强的字段

| 表 | 建议 |
|---|---|
| `novel_chapter` | 增加 `start_offset`, `end_offset`, `volume_number`, `volume_title` |
| `novel_chunk` | 增加 `start_offset`, `end_offset`, `chunk_no`, `token_count` |
| `novel_chapter_fact` | 增加 `fact_json`, `model_run_id`, `evidence_text`, `raw_output_ref` |
| `novel_model_run` | 长期建议用 `raw_input_ref`, `raw_output_ref` 替代直接存完整文本 |
| `novel_user` | 不建议明文密码；要么 demo 不做登录，要么字段改为 `password_hash` |
| `novel_citation` | 保留 `source_type`, `source_id`，同时冗余 `chapter_id/chunk_id/fact_id` 方便查询 |

## 从 AI-reader 吸收的点

- `chapter_facts.fact_json` 适合做 schema 演进。
- 角色经历可从事件参与者推导，不必一开始建复杂经历表。
- 章节切分需要多策略和回退，但 demo 可以先简化。
- 实体词典对抽取准确率有帮助，可放到 v1-hardening。

## 不建议照搬的点

- AI-reader 使用 SQLite + 运行时聚合；本项目目标有 Spring Boot + MySQL + 可审核资产，不能完全照搬“不持久化角色档案”。
- 本项目强调 Citation、AgentRun、ModelRun，这些比 AI-reader 的纯分析可视化场景更重要。
