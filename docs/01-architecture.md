# NovelBridge Architecture

## High-Level Shape

```text
Web UI / Desktop later
        |
        v
Java Spring Boot product API
        |
        v
Python FastAPI rag-agent
        |
        +--> DeepSeek API
        +--> local llama-server / 9B
        +--> rules and traditional NLP
        |
        v
MySQL/PostgreSQL source-of-truth
Qdrant vector retrieval
Neo4j narrative graph projection later
```

## Java Product API

Java remains useful for the interactive product layer:

- book upload and metadata APIs;
- chat sessions and citation APIs;
- build task status APIs;
- review workflow APIs;
- user/project/workspace APIs later;
- SSE/WebSocket progress fanout;
- frontend-facing aggregation.

Java should not implement heavy NLP, model prompting, or graph projection. It delegates AI work to `rag-agent`.

## Python rag-agent

Python owns AI execution:

- encoding-aware text ingestion checks;
- text cleanup, chapter splitting, chunking;
- rule and NLP candidate generation;
- model provider abstraction;
- prompt rendering and structured parsing;
- ChapterFact draft generation;
- evidence validation;
- vector indexing;
- Neo4j projection after validation.

## Data Stores

Start with one relational source-of-truth.

Recommended default: MySQL 8.4 with `utf8mb4`.

PostgreSQL is also reasonable, especially if we later want JSONB and full-text search. For the current remote environment and existing scripts, MySQL remains the lower-friction choice.

Vector database:

- Qdrant is the default vector database from the start.
- Qdrant stores dense chunk vectors first, then ChapterFact/entity/event vectors later.
- Payload filters must include `book_id`, `chapter_id`, `chunk_id`, and later `entity_id` / `plot_stage_id`.

Embedding model:

- Default: `Qwen/Qwen3-Embedding-0.6B`
- Initial output dimension: `1024`
- Distance: cosine
- Primary use: chunk retrieval and ChapterFact retrieval
- Later use: entity, event, plotline, and card retrieval

Neo4j:

- Do not use as the primary fact store.
- Use it as a projection from reviewed/high-confidence relational facts.

## Retrieval Architecture

NovelBridge uses Evidence-first Hybrid RAG:

```text
query understanding
  -> lexical retrieval
  -> dense retrieval with Qwen3-Embedding-0.6B + Qdrant
  -> structured retrieval from ChapterFact
  -> fusion, preferably RRF
  -> rerank later
  -> answer with citations
```

BM25-style lexical retrieval is still useful for names, chapter titles, exact source phrases, and rare terms. It should be combined with dense retrieval rather than replaced by it.

## Encoding Policy

Internal text is Unicode and persisted through UTF-8/`utf8mb4`.

Uploaded files may be UTF-8, UTF-8 BOM, GB18030, GBK, or other encodings. Decode once at ingestion, record the detected/provided encoding, store normalized text as Unicode, and hash the original bytes.

## Remote Structure

Remote deployment follows `STRUCTURE.md`:

```text
/home/wk/novelbridge/
  apps/rag-agent/
  deploy/remote/
  scripts/remote/
  docs/
  training/
  models/
  data/
  env/
  runtime/
  logs/
```

Keep `ports.env`, `.env`, model files, data volumes, and LLaMA-Factory protected.
