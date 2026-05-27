# Pipeline

## Stage Flow

```text
Import source
  -> decode and normalize text
  -> split chapters
  -> build chunks (800-1500 chars, paragraph-preferring)
     └── smart split at ~50% for >50K chars (Qwen3-Embedding-0.6B limit)
         with parent_chunk_id + split_index relationship tracking
  -> generate candidate hints
  -> extract mentions
  -> build ChapterFact
  -> validate evidence
  -> index retrieval (BATCH_SIZE=2, PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True)
  -> answer with citations
```

## Import

Input:

- TXT first.
- Markdown/EPUB later.

Rules:

- compute `source_hash` from original bytes;
- detect or accept source encoding;
- normalize internal text to UTF-8;
- store file metadata and source text;
- reject or version duplicate uploads deliberately, not by raw DB error.

## Split

Start deterministic:

- Chinese chapter patterns: `第...章/回/节/卷/篇`
- story collection patterns later;
- fallback fixed sections when structure is unclear.

Low-confidence structure can call DeepSeek for strategy review, but source text decides boundaries.

## Chunk

Rules:

- do not cross chapter;
- prefer paragraph boundary;
- keep offsets;
- store content hash;
- target around 800-1500 Chinese chars at first.

## Candidate Hints

Use:

- high-frequency names;
- jieba/n-gram;
- dialogue attribution;
- entity suffixes;
- relation triggers;
- event triggers;
- book prior hints as strategy only.

## ChapterFact

ChapterFact contains:

```json
{
  "chapter_id": 1,
  "chapter_summary": "",
  "characters": [],
  "relations": [],
  "events": [],
  "locations": [],
  "items": [],
  "organizations": [],
  "concepts": [],
  "evidence_records": [],
  "quality_flags": []
}
```

Every accepted fact must link to evidence.

## Validation

Evidence levels:

- `EXACT`
- `NORMALIZED`
- `NEAR`
- `IMPLICIT_LOCAL`
- `UNSUPPORTED`

Entity existence requires `EXACT` or `NORMALIZED`. Relations/events may allow constrained local inference but must remain reviewable.

## Export

Dataset export is not part of the first pipeline. It belongs after evaluation and review exist.
