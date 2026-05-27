# Data Model V1

## Principle

Start with a small source-grounded schema. Do not recreate the old 26-table training pipeline.

The central intermediate asset is `novel_chapter_fact`, not Neo4j and not a global entity table.

## Core Tables

| Table | Purpose |
|---|---|
| `novel_book` | imported book metadata and normalized source text pointer/status |
| `novel_chapter` | deterministic chapter/section split |
| `novel_chunk` | retrieval and extraction unit |
| `novel_chapter_fact` | structured per-chapter fact JSON with evidence |
| `novel_agent_run` | one long-running task |
| `novel_agent_step` | one step inside a task |
| `novel_model_call` | one model invocation |
| `novel_chat_session` | user conversation on a book |
| `novel_chat_message` | chat messages |
| `novel_citation` | source evidence attached to an answer |

## Later Tables

Add only when needed:

- `novel_entity_mention`
- `novel_entity_profile`
- `novel_alias_decision`
- `novel_review_item`
- `novel_relation_mention`
- `novel_relation_fact`
- `novel_event_mention`
- `novel_event_fact`
- `novel_plot_stage`
- `novel_eval_case`
- `novel_eval_run`
- `novel_eval_result`

## Qdrant Collections

Qdrant is the default vector database.

Initial collections:

| Collection | Vector | Payload |
|---|---|---|
| `novel_chunks` | Qwen3-Embedding-0.6B, 1024 dim, cosine | `book_id`, `chapter_id`, `chunk_id`, `chapter_number`, `start_offset`, `end_offset`, `content_hash` |
| `novel_chapter_facts` | Qwen3-Embedding-0.6B, 1024 dim, cosine | `book_id`, `chapter_id`, `chapter_fact_id`, `review_status`, `evidence_status` |

Later collections:

- `novel_entities`
- `novel_events`
- `novel_plotlines`

Relational DB remains the source of truth. Qdrant stores retrieval indexes and payloads needed for filtering.

## Encoding Fields

Book ingestion must store:

- `source_file_name`
- `source_encoding`
- `source_hash`
- `char_count`
- `language`

The hash is computed from original bytes. Text stored in DB is normalized Unicode through UTF-8/`utf8mb4`.

## JSON Fields

Use JSON fields for evolving model outputs:

- `chapter_fact.fact_json`
- `chapter_fact.evidence_json`
- `model_call.request_json`
- `model_call.response_json`

Stable frequently queried fields remain columns.

## Status Discipline

Use clear statuses:

- task status: `PENDING | RUNNING | SUCCESS | FAILED | CANCELED`
- parse status: `SUCCESS | JSON_REPAIRED | FAILED`
- evidence status: `EXACT | NORMALIZED | NEAR | UNSUPPORTED | NOT_CHECKED`
- review status: `PENDING | ACCEPTED | REVISED | REJECTED | MANUAL_REVIEW`
