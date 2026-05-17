# NovelBridge Remote Agent Instructions

This document is for the remote development agent running on the Linux server.

The remote agent should be restricted to:

```text
/home/wk/novelbridge
```

Do not read or write outside this directory unless the user explicitly asks.

## Role

You are the remote-side implementation agent for NovelBridge AI services.

Your long-term ownership includes:

```text
apps/rag-agent/
llama.cpp integration
book structure analysis
chapter splitting
chunk generation
structured extraction runners
prompt / schema / grammar assets
model call tracing
candidate validation and review support
Neo4j graph writes
Chroma/vector indexing
evaluation and data export helpers
```

Current stage:

```text
Demo 5B: remote book decomposition + chunking + model_run + entity candidate + minimal review/graph write
```

Build a small, verifiable extraction loop first. Do not jump to relation/event/claim extraction, full GraphRAG QA, or fine-tuning until the user explicitly moves the project forward.

## Main Architecture

NovelBridge has three main layers:

```text
Local Spring Boot backend
  - uploads or registers a book
  - connects to remote MySQL only for the book-source upload table
  - writes the whole TXT/book content into that table
  - triggers the remote rag-agent to build downstream artifacts
  - remains the user-facing business/API entry

Remote Python rag-agent
  - reads whole-book source text from remote MySQL
  - analyzes book structure
  - splits chapters/sections with rule-based logic and optional LLM assistance
  - creates chunks
  - calls llama.cpp for structured entity extraction
  - parses and validates model output
  - writes trace/candidate/review/graph/vector artifacts

Remote services
  - MySQL: source-of-truth and audit database
  - llama-server: local OpenAI-compatible inference endpoint
  - Neo4j: approved knowledge graph
  - Chroma: chunk vector index with metadata for MySQL lookup
```

For Demo 5B, prefer deterministic, auditable workflow runners over a free-form ReAct agent.

Current workflow:

```text
book_source -> structure analysis -> chapter -> chunk -> llama.cpp -> parse -> validate
  -> model_run -> entity_candidate -> review -> entity_profile / minimal Neo4j
```

Do not implement ReAct planning unless explicitly requested. If agentic planning becomes useful later, add it behind a narrow runner boundary with full trace records.

## Remote Data Ownership

The local Java backend should write only the upload/source table on remote MySQL.

Recommended upload/source table:

```text
novel_book_source
```

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

Demo-stage rule:

```text
The whole TXT/book content is stored once in novel_book_source.raw_text.
```

The remote rag-agent owns downstream generated artifacts:

```text
novel_book
novel_chapter
novel_chunk
novel_agent_run
novel_agent_step
novel_model_run
novel_entity_candidate
novel_review_record
novel_entity_profile
```

If the existing schema uses `novel_book` as the upload table, keep the same principle: Java writes only that one book-source table, and rag-agent creates the chapter/chunk/extraction artifacts.

## Chapter Storage Rule

Store chapters even though the full book text is already stored.

Reason:

```text
chapter = reading/citation/progress boundary
chunk = model/vector processing boundary
```

The chapter table does not need to duplicate full text forever. Preferred design:

```text
novel_chapter
  id
  book_source_id
  book_id
  chapter_number
  title
  structure_type        # CHAPTER / HUI / STORY / SECTION / AUTO / NONE
  start_offset          # offset in whole-book raw_text
  end_offset            # offset in whole-book raw_text
  raw_content           # nullable cache for Demo convenience
  cleaned_content       # nullable cache for model input
  char_count
  splitter_version
  status
  error_message
```

For Demo 5B, it is acceptable to store `raw_content`/`cleaned_content` in `novel_chapter` as a cache. The canonical immutable source remains `novel_book_source.raw_text` plus offsets and content hash.

The rag-agent may use LLM assistance to classify book structure:

```text
regular chapter novel
chapter/hui format
mixed section format
story collection such as Liaozhai
classic text such as Shanhaijing
no obvious chapters
```

Do not rely on the LLM as the only splitter. Use rules first, then LLM-assisted classification or boundary proposal when rules are uncertain. Persist splitter version and confidence/error state.

## Chunk Storage Rule

Chunks must be persisted in MySQL before or during extraction.

Recommended table:

```text
novel_chunk
```

Recommended fields:

```text
id
book_source_id
book_id
chapter_id
chunk_index
chunk_uid
text
start_offset          # offset within chapter, or clearly documented global offset
end_offset
char_count
token_count
chunk_strategy
chunk_version
content_hash
vector_status         # NOT_INDEXED / INDEXED / FAILED
embedding_id          # Chroma id
status
error_message
```

Chunking rule for Demo 5B:

```text
800-1500 Chinese characters per chunk
150-300 character overlap
do not cross chapter boundaries when chapters exist
prefer paragraph boundaries
if no chapters exist, split the whole source into stable sections/chunks
```

## Vector Store Rule

Chroma stores the retrieval index, not the business source of truth.

Use:

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

Always keep MySQL IDs in Chroma metadata so retrieval can resolve back to MySQL records.

Do not treat Chroma metadata as the authoritative source for book text, chapter boundaries, model outputs, review state, or citations.

For Demo 5B, Chroma indexing may be implemented after entity extraction if needed. At minimum, keep `novel_chunk.vector_status` and `embedding_id` ready.

## Neo4j Mapping Rule

Neo4j stores approved graph knowledge, not raw model candidates and not full book text.

Minimal graph after review approval:

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

All Neo4j nodes and relationships must carry MySQL IDs for round-trip lookup.

Do not write unreviewed candidates as final graph truth. If temporary graph writes are needed for debugging, mark them clearly with `status = "AUTO_EXTRACTED"` or `mock = true`.

## Model Call And Candidate Rules

Every llama.cpp call must create a `novel_model_run` or equivalent trace record.

Recommended fields:

```text
id
agent_step_id
book_source_id
book_id
chapter_id
chunk_id
task_type
model_name
model_endpoint
prompt_version
schema_version
grammar_version
input_text or input_ref
output_text or output_ref
parse_status
status
error_type
error_message
retry_count
duration_ms
created_at
```

Entity candidates should be stored in:

```text
novel_entity_candidate
```

Minimal fields:

```text
id
book_source_id
book_id
chapter_id
chunk_id
model_run_id
name
entity_type
aliases_json
description
evidence_text
confidence
uncertain
status
error_message
created_at
updated_at
```

Validation requirements:

```text
- JSON parse succeeds.
- Required fields exist.
- entity_type is in the allowed enum.
- confidence is between 0 and 1.
- name is not empty.
- evidence_text is not empty.
- evidence_text appears in the source chunk.
```

Minimal entity schema:

```json
{
  "entities": [
    {
      "name": "string",
      "type": "CHARACTER | LOCATION | ITEM | ORG | TITLE | UNKNOWN",
      "aliases": ["string"],
      "description": "string",
      "evidence_text": "string",
      "confidence": 0.0,
      "uncertain": false
    }
  ],
  "uncertain_items": ["string"]
}
```

## Recommended rag-agent Structure

Use this structure or adapt the existing one conservatively:

```text
apps/rag-agent/
  app/
    main.py
    api/
      health.py
      books.py
      extract.py
      review.py
    clients/
      llama_cpp_client.py
      mysql_client.py
      neo4j_client.py
      chroma_client.py
    runners/
      book_build_runner.py
      chapter_split_runner.py
      chunk_build_runner.py
      entity_extraction_runner.py
    schemas/
      book_build.py
      entity_extract.py
    prompts/
      chapter_structure_v0_1.txt
      entity_extract_v0_1.txt
    validators/
      evidence_validator.py
      extraction_validator.py
    stores/
      book_source_store.py
      chapter_store.py
      chunk_store.py
      model_run_store.py
      candidate_store.py
      graph_store.py
      vector_store.py
    memory/
      extraction_context.py
  tests/
```

For Demo 5B, memory means engineering memory, not chatbot memory:

```text
run/step state
book structure analysis result
chapter/chunk IDs and offsets
model_run prompt/output/error
chunk-local entity context
review decisions
approved graph state
```

Do not add LangChain, LangGraph, or ReAct unless the user explicitly asks. Keep dependencies small.

## Important Paths

Remote root:

```text
/home/wk/novelbridge
```

Important directories:

```text
/home/wk/novelbridge/apps/rag-agent
/home/wk/novelbridge/deploy/remote
/home/wk/novelbridge/docs/learn
/home/wk/novelbridge/.opencode/skills/vibe-learn
/home/wk/novelbridge/.vtl
```

Runtime/data directories:

```text
/home/wk/novelbridge/data
/home/wk/novelbridge/logs
/home/wk/novelbridge/runtime
/home/wk/novelbridge/models
/home/wk/novelbridge/env
```

Treat runtime/data directories as operational state. Do not commit their contents. Do not overwrite them unless the user explicitly asks.

## Service Ports

```text
MySQL:        127.0.0.1:13306
Neo4j HTTP:   127.0.0.1:17474
Neo4j Bolt:   127.0.0.1:17687
llama-server: 127.0.0.1:18080
rag-agent:    0.0.0.0:18081
```

Use llama.cpp through its OpenAI-compatible API. Prefer checking:

```text
GET http://127.0.0.1:18080/v1/models
```

Do not rely only on `/health` for llama-server.

## Required Reads

Read these first if present:

```text
/home/wk/novelbridge/AGENTS.md
/home/wk/novelbridge/.opencode/skills/vibe-learn/SKILL.md
/home/wk/novelbridge/.vtl/vtl-adapter.json
/home/wk/novelbridge/docs/learn/current-stage.md
/home/wk/novelbridge/docs/learn/demo-plan.md
/home/wk/novelbridge/docs/learn/demo-5b-remote-data-flow.md
/home/wk/novelbridge/docs/learn/remote-server-structure.md
/home/wk/novelbridge/docs/learn/table-design-review.md
/home/wk/novelbridge/docs/learn/table-design.md
```

Do not read `docs/private/` unless the user explicitly asks.

## Demo 5B Minimal Scope

Implement this loop first:

```text
1. Receive a build/extract trigger for one uploaded book_source_id.
2. Read whole-book raw_text from remote MySQL.
3. Analyze structure and split chapters/sections.
4. Persist chapters with offsets and optional text cache.
5. Build chunks and persist them.
6. For each chunk, call llama-server for entity extraction.
7. Parse, validate, and evidence-check model output.
8. Save raw prompt/output/status/error to model_run.
9. Save valid entities as candidates.
10. Provide minimal review operation: approve / reject / edit.
11. On approval, write entity_profile and minimal Neo4j nodes/edges.
```

Chroma indexing is optional for the first Demo 5B pass. If implemented, it must index `novel_chunk` and carry MySQL IDs in metadata.

## Hard Rules

- Keep Demo 5B small and verifiable.
- Mark mock or temporary behavior explicitly.
- Local Java writes only the remote book-source upload table for this flow.
- Remote rag-agent owns chapter splitting, chunking, model extraction, validation, candidate generation, and optional graph/vector writes.
- Do not skip `AgentRun` / `AgentStep` for long-running build or extraction flows.
- Every model call must create a `ModelRun` or equivalent trace.
- Do not call QA complete without `Citation`.
- Do not implement relation/event/claim extraction in Demo 5B.
- Do not implement full GraphRAG in Demo 5B.
- Do not write server passwords, database passwords, Neo4j passwords, API tokens, SSH keys, or real `.env` values into tracked files.
- Do not overwrite raw prompt/output/error records.
- Candidate extraction results are not truth. They must be reviewed before becoming approved graph data.

## Health and Verification

Useful commands:

```bash
cd /home/wk/novelbridge/deploy/remote
bash nb_status.sh
bash nb_healthcheck.sh --json
```

Check rag-agent:

```bash
curl http://127.0.0.1:18081/health
```

Check llama-server:

```bash
curl http://127.0.0.1:18080/v1/models
```

Run Python tests if available:

```bash
cd /home/wk/novelbridge/apps/rag-agent
python -m pytest
```

If pytest is not installed, do not blindly install global packages. Ask the user or use the existing venv if configured.

## Sync Back To Local

The local repository should remain the main commit source.

Recommended flow:

```text
local repo = git commit source
remote /home/wk/novelbridge = runtime and remote development environment
remote changes -> whitelist sync back to local -> local diff/test/review -> local commit
```

Sync only these directories unless the user says otherwise:

```text
/home/wk/novelbridge/apps/rag-agent       -> local rag-agent
/home/wk/novelbridge/deploy/remote        -> local deploy/remote
/home/wk/novelbridge/docs/learn           -> local docs/learn
/home/wk/novelbridge/.opencode/skills     -> local .opencode/skills
/home/wk/novelbridge/.vtl                 -> local .vtl
```

Do not sync:

```text
data
logs
runtime
models
env
.env
*.pid
*.log
__pycache__
.venv
```

VS Code manual transfer is acceptable for the first iteration, but the agent must report changed files clearly so the user can pull back the exact files.

## Development Output

When finishing a stage, report:

```text
Changed files
Implemented behavior
Mock/debt still present
Verification commands and results
Files that should be synced back to local Windows repo
```

Do not claim Demo 5B complete unless the remote flow has book source input, chapter/chunk artifacts, model_run trace, candidates, review, and verification evidence.
