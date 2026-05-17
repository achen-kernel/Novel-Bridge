# Demo 5B Remote Data Flow

This document records the current Demo 5B architecture decision.

## Decision

Local Java uploads the whole book to one remote MySQL book-source table, then triggers the remote `rag-agent`.

The remote `rag-agent` owns:

```text
book structure analysis
chapter splitting
chunk generation
LLM entity extraction
model_run tracing
candidate generation
minimal review support
optional vector indexing
approved minimal Neo4j graph write
```

## Flow

```text
Local Spring Boot
  -> writes whole TXT/book content to remote MySQL book-source table
  -> sends trigger to remote rag-agent with book_source_id

Remote rag-agent
  -> reads whole-book raw_text from MySQL
  -> detects structure: chapter / hui / story / section / no obvious chapter
  -> persists chapter records
  -> builds chunks
  -> persists chunk records
  -> calls llama.cpp for entity extraction
  -> writes model_run records
  -> writes entity candidates
  -> supports approve / reject / edit
  -> approved data writes entity_profile and minimal Neo4j graph
```

## MySQL Role

MySQL is the source-of-truth and audit database.

Recommended source table:

```text
novel_book_source
```

For Demo 5B, Java should write only this table in the remote database.

Minimal fields:

```text
id
title
author
source_filename
file_type
file_size
content_hash
raw_text
encoding
status
error_message
created_at
updated_at
```

If the existing schema keeps the upload content in `novel_book`, keep the same ownership rule: Java writes only the one book-source table, and rag-agent creates downstream generated artifacts.

## Chapter Storage

Store chapter records even though the full book source is stored.

Reason:

```text
chapter = reading, progress, and citation boundary
chunk = model and vector processing boundary
```

The chapter table does not need to duplicate full text forever. Preferred design:

```text
novel_chapter
  id
  book_source_id
  book_id
  chapter_number
  title
  structure_type
  start_offset
  end_offset
  raw_content        # nullable cache
  cleaned_content    # nullable cache
  char_count
  splitter_version
  status
  error_message
```

Demo 5B may store `raw_content` and `cleaned_content` as a cache for simplicity. The canonical source is still `novel_book_source.raw_text` plus offsets and content hash.

## Chunk Storage

Chunks must be persisted in MySQL.

Recommended fields:

```text
novel_chunk
  id
  book_source_id
  book_id
  chapter_id
  chunk_index
  chunk_uid
  text
  start_offset
  end_offset
  char_count
  token_count
  chunk_strategy
  chunk_version
  content_hash
  vector_status
  embedding_id
  status
  error_message
```

Demo chunking rule:

```text
800-1500 Chinese characters
150-300 character overlap
do not cross chapter boundaries when chapters exist
prefer paragraph boundaries
if no chapters exist, build stable pseudo-sections/chunks
```

## Chroma Role

Chroma is a retrieval index, not the source-of-truth.

Recommended mapping:

```text
Chroma id = novel_chunk.chunk_uid or novel_chunk.id
document = novel_chunk.text
metadata = {
  book_source_id,
  book_id,
  chapter_id,
  chunk_id,
  chapter_number,
  chunk_index,
  start_offset,
  end_offset,
  content_hash,
  chunk_version
}
```

Chroma metadata must always carry MySQL IDs so retrieval can resolve back to MySQL.

For Demo 5B, Chroma indexing is optional after entity extraction. Keep `novel_chunk.vector_status` and `embedding_id` ready even if indexing is deferred.

## Neo4j Role

Neo4j stores approved graph knowledge.

It should not be the only place where raw text, candidates, review decisions, or model outputs exist.

Minimal approved graph:

```text
(:Book {book_id, book_source_id})
(:Chapter {chapter_id, book_id, chapter_number, title})
(:Chunk {chunk_id, chapter_id, book_id, chunk_index})
(:Entity {entity_profile_id, book_id, name, type})
```

Minimal relationships:

```text
(:Book)-[:HAS_CHAPTER]->(:Chapter)
(:Chapter)-[:HAS_CHUNK]->(:Chunk)
(:Entity)-[:APPEARS_IN {
  candidate_id,
  model_run_id,
  evidence_text,
  confidence,
  status,
  reviewed_at
}]->(:Chunk)
```

All graph data must carry MySQL IDs for traceability.

## Demo 5B Completion Line

Demo 5B is not complete until:

```text
1. A whole book is stored in the remote book-source table.
2. rag-agent can read the source by book_source_id.
3. rag-agent creates chapter records.
4. rag-agent creates chunk records.
5. at least one chunk calls llama.cpp.
6. model_run records raw prompt/output/status/error.
7. entity candidates include chunk_id and evidence_text.
8. evidence_text is validated against chunk text.
9. review approve/reject/edit exists at least as an API.
10. approved entity can be written to entity_profile and minimal Neo4j graph.
```
