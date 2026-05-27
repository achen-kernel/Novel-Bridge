# ReaderAgent Contract v0.1

本文定义 `ReaderAgent` 的早期合同。它不是只做 QA 的 Agent，而是面向阅读、分析、追踪和知识反哺的在线 Agent。

## 1. 目标

`ReaderAgent` 负责在线任务：

- 回答用户关于小说内容的问题。
- 分析人物、关系、事件、设定和章节。
- 追踪伏笔、物件、能力、设定变化和人物关系变化。
- 学习描述、描写、叙事节奏和风格样本。
- 提出知识库补全建议，但不直接写正式知识库。

第一阶段只实现 `answer` mode 的 Agent 外壳，并复用现有 `app/qa`。

## 2. Mode

| Mode | 阶段 | 说明 |
|---|---|---|
| `answer` | Stage 3D | 基于证据回答问题，返回 citation/evidence/trace |
| `analyze` | Stage 3D/B | 分析人物、关系、章节、设定 |
| `trace` | Stage B | 追踪伏笔、物件、能力、关系变化 |
| `enrich` | Stage B | 生成 KnowledgePatch candidate |
| `learn_style` | Stage C | 学习描写、叙事风格、节奏 |
| `authoring` | Stage C | 创作辅助，必须受已验证知识约束 |

早期只允许 `answer` 和最小 `analyze`。

## 3. 状态机

标准路径：

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

知识反哺路径：

```text
PATCH_DRAFTED
-> PATCH_VALIDATED
-> PATCH_PENDING_REVIEW
```

失败/暂停状态：

```text
NEED_FOLLOWUP
INSUFFICIENT_EVIDENCE
FAILED
CANCELED
```

约束：

- Planner 只能建议下一步 Action。
- 状态机必须在代码层验证转移是否合法。
- Evidence 不足时不能强行进入 `VERIFIED`。
- `RESPONDED` 前必须有回答文本或明确拒答原因。

## 4. 输入合同

```json
{
  "mode": "answer",
  "book_id": 6,
  "question": "孙悟空为什么三打白骨精？",
  "session_id": null,
  "scope": {
    "chapter_ids": [],
    "entity_ids": [],
    "time_range": null
  },
  "options": {
    "provider": "local",
    "require_citations": true,
    "allow_patch": false,
    "top_k": 12
  }
}
```

字段规则：

- `book_id` 必填。
- `question` 在 `answer/analyze/trace/enrich` 中必填。
- `session_id` 可空；为空时由 QA 层或会话层创建。
- `allow_patch=false` 时不得生成 KnowledgePatch。
- `require_citations=true` 时无 citation 必须返回 `INSUFFICIENT_EVIDENCE` 或明确低置信回答。

## 5. 输出合同

```json
{
  "run_id": 123,
  "mode": "answer",
  "status": "RESPONDED",
  "answer": "...",
  "citations": [],
  "evidence": [],
  "trace_id": 456,
  "patches": [],
  "errors": []
}
```

字段规则：

- `status` 必须是状态机状态。
- `citations` 必须能回到 L2 证据。
- `patches` 只能是候选补丁，不能代表正式写库。
- `trace_id` 用于调试检索路径。

## 6. API 草案

早期 API：

```text
POST /api/reader-agent/run
GET  /api/reader-agent/runs/{run_id}
GET  /api/reader-agent/runs/{run_id}/trace
```

兼容规则：

- 不删除现有 `/api/qa/ask`。
- 新 API 初期可不接 UI，只用于调试和后续迁移。
- 旧 QA API 的行为不因 ReaderAgent 骨架而改变。

## 7. Evidence 规则

ReaderAgent 可使用：

- 原文 chunk。
- ChapterFact。
- validated entity/relation/event。
- citation。

ReaderAgent 不可把以下内容当成事实证据：

- L0 摘要。
- L1 结构化要点。
- 会话记忆。
- 模型生成的无引用判断。

## 8. 与现有代码的关系

| 现有模块 | ReaderAgent 用法 |
|---|---|
| `app/qa/qa_runner.py` | `answer` mode 的底层服务 |
| `app/qa/retrieval_runner.py` | evidence search 工具 |
| `app/stores/qa_store.py` | 会话与 QA 存储 |
| `app/eval/` | 后续评测 ReaderAgent answer mode |
| `app/quality/` | 后续把质量问题转成 patch candidate |

## 9. 后续填充任务

给后续 Agent 的实现顺序：

1. 在 `app/reader_agent/modes/answer.py` 中接入 `QaRunner.answer()`。
2. 为 answer mode 写 retrieval trace。
3. 在 `agent_runtime/citation_verifier.py` 中校验 citations。
4. 新增 `/api/reader-agent/run`，但不影响旧 `/api/qa/ask`。
5. 增加 answer mode 的 smoke test。

