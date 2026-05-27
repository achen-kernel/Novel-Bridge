# 2026-05-20 Book 8 Pipeline Notes

## Repair Record

Book 8 (`搜神记`) exposed three data-chain issues after the merged pipeline run:

- `event_mentions=243` but `event_facts=0`.
- `facts_indexed=30, failed=5`.
- export errors displayed as `unknown`.

Changes made:

- `apps/rag-agent/app/runners/narrative_builder.py`
  - Event aggregation now accepts `summary`, `description`, `event_summary`, or `evidence_text`.
- `apps/rag-agent/app/runners/extraction_runner.py`
  - Rule fallback now generates a non-empty `chapter_summary`.
  - `extract_chunk` defaults to model mode.
- `apps/rag-agent/app/runners/chapter_fact_builder.py`
  - ChapterFact build now provides a summary fallback from events, entities, or chapter title.
- `apps/rag-agent/app/stores/vector_index_store.py`
  - Fact indexing falls back to `fact_json` text when `summary` is empty.
- `apps/rag-agent/app/runners/dataset_exporter.py`
  - Error responses now include both `message` and `error`.
- `apps/rag-agent/app/api/eval.py`
  - `ExportResponse` includes `error`.
- `apps/rag-agent/app/api/facts.py`
  - Extract API defaults to `use_model=true`.
- `apps/rag-agent/app/runners/fact_pipeline_runner.py`
  - Fact pipeline defaults to model mode.
- `apps/rag-agent/app/prompts/extraction_output.gbnf`
  - Entity, relation, and event arrays now allow `[]`.

Verification:

- Local AST syntax check passed for 59 Python files.

## Lessons

Every model-output field must be checked through:

```text
prompt -> grammar -> parser -> builder -> store -> index/export
```

Route success counts are not data quality evidence. A successful stage can still silently drop events, summaries, or export errors if field names drift.

Constrained decoding should enforce shape, not force content. Empty arrays are valid extraction output when a chunk has no supported entity, relation, or event.

## Per-Book Rule Strategy

NovelBridge should support both general rules and book-specific adaptive rules.

General rules belong in code/config:

- shared chunking defaults
- generic entity blacklist
- generic alias safety rules
- common relation/event schemas
- grammar and response shape

Book-specific rules should be generated and stored as versioned data artifacts:

- prior hints
- chapter title patterns
- named dictionaries
- entity focus
- relation focus
- event taxonomy
- alias risks
- merge/block rules
- extraction prompt deltas

Minimum metadata:

- `book_id`
- `prompt_revision`
- `schema_revision`
- `provider/model`
- source or reason
- review status
- downstream stages affected

## Training Data Rule

Training data is a first-class pipeline output, not an afterthought.

Useful samples should include:

- prompt input
- model raw output
- parsed candidate output
- validated ChapterFact
- evidence status
- review status
- failure labels when parsing/evidence fails

Use `PENDING` exports only for smoke tests. Fine-tuning data should come from reviewed `ACCEPTED` facts or explicitly labeled negative/error cases.
