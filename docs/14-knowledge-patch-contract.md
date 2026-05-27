# KnowledgePatch Contract v0.1

本文定义 `KnowledgePatch` 的候选补丁合同。它用于让 `ReaderAgent` 和质量流程反哺知识库，但不能绕过审核直接修改正式知识表。

## 1. 目标

`KnowledgePatch` 解决的问题：

- QA/阅读过程中发现知识库缺失。
- 检索发现 citation 不充分或错位。
- 质量流程发现别名、关系、事件、设定存在问题。
- 用户反馈可转成可审核候选。

核心规则：

```text
Patch 是候选，不是真值。
Evidence 和 review 决定是否接受。
```

## 2. 状态

正常流程：

```text
PROPOSED
-> SCHEMA_VALIDATED
-> AUTO_VALIDATED
-> PENDING_REVIEW
-> ACCEPTED
-> MERGED
```

终止或暂停：

```text
REJECTED
NEEDS_MORE_EVIDENCE
SUPERSEDED
CANCELED
```

约束：

- `MERGED` 只能由明确的 merge service 执行。
- `ReaderAgent` 最多推进到 `PENDING_REVIEW`。
- 高风险 patch 不能自动进入 `ACCEPTED`。

## 3. Patch 类型

| 类型 | 风险 | 说明 |
|---|---|---|
| `citation_fix` | low | 修复或补充引用 |
| `context_summary_update` | low | 更新 L0/L1 摘要 |
| `style_sample_add` | low | 新增风格样本候选 |
| `event_add` | medium | 新增事件候选 |
| `relation_stage_add` | medium | 新增阶段性关系 |
| `setting_update` | medium | 新增或修正设定 |
| `foreshadowing_link` | medium | 建立伏笔与回收关系 |
| `alias_add` | high | 新增别名 |
| `alias_block` | high | 禁止错误别名 |
| `entity_split` | critical | 拆分实体 |
| `entity_merge` | critical | 合并实体 |
| `validator_rule_candidate` | medium | 新增校验规则候选 |
| `eval_case_candidate` | low | 新增评测样例候选 |

## 4. 输入 Schema

```json
{
  "book_id": 6,
  "patch_type": "foreshadowing_link",
  "target_type": "event",
  "target_id": 123,
  "payload": {},
  "evidence": [
    {
      "source_type": "chunk",
      "source_id": 456,
      "chapter_id": 12,
      "excerpt": "...",
      "evidence_level": "DIRECT"
    }
  ],
  "risk_level": "medium",
  "created_by": "reader_agent",
  "run_id": 789
}
```

## 5. 必填规则

所有 Patch 必填：

- `book_id`
- `patch_type`
- `payload`
- `evidence`
- `risk_level`
- `created_by`

高风险 Patch 额外要求：

- `alias_add` 必须说明别名出现章节和上下文。
- `alias_block` 必须说明容易误合并的两个名字。
- `entity_split` 必须给出拆分后的候选实体和冲突证据。
- `entity_merge` 必须给出同一性证据和反证检查结果。

## 6. Evidence 规则

允许作为证据：

- `chunk`
- `chapter_fact`
- `entity`
- `relation`
- `event`
- `citation`

不允许作为最终事实证据：

- `context_l0`
- `context_l1`
- `session_memory`
- 无引用模型输出

## 7. 表结构草案

后续 migration 可新增：

```text
novel_knowledge_patch
novel_knowledge_patch_evidence
novel_patch_review
```

早期字段建议：

```text
id
book_id
patch_type
target_type
target_id
payload_json
risk_level
status
created_by
run_id
created_at
updated_at
reviewed_by
reviewed_at
review_note
```

## 8. API 草案

```text
GET  /api/knowledge-patches
GET  /api/knowledge-patches/{patch_id}
POST /api/knowledge-patches/{patch_id}/review
```

早期不提供自动 merge API。

## 9. 后续填充任务

给后续 Agent 的实现顺序：

1. 在 `app/knowledge_patch/schemas.py` 固化 Patch schema。
2. 在 `validator.py` 实现风险级别和 evidence 校验。
3. 在 `store.py` 接入 MySQL。
4. 在 `service.py` 实现 propose/review 查询。
5. ReaderAgent 的 `enrich` mode 只能调用 propose，不调用 merge。

