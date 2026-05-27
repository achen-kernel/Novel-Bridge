# RAG Strategy

## Recommendation

Do not start with full GraphRAG.

Start with Evidence-first Hybrid RAG, then Entity-aware RAG, then Narrative GraphRAG.

Fixed retrieval technology decisions:

```text
Vector database: Qdrant
Embedding model: Qwen/Qwen3-Embedding-0.6B
Embedding dimension: 1024
Vector distance: cosine
Fusion: RRF once both lexical and dense retrieval are available
```

## Phase R1: Evidence-First RAG

Retrieval sources:

- chunks;
- chapter summaries;
- ChapterFact JSON;
- exact keyword/BM25-style lexical matches;
- dense vector retrieval through Qdrant;
- structured ChapterFact retrieval.

Retrieval flow:

```text
query
  -> identify book/chapter/entity hints
  -> lexical retrieval for exact names and phrases
  -> dense retrieval for semantic matches
  -> ChapterFact retrieval for structured facts
  -> fuse candidates
  -> cite source chunks/facts
```

Answer requirement:

- every answer must include citations;
- unsupported questions should say evidence is insufficient;
- model memory cannot replace source evidence.

## Phase R2: Entity-Aware RAG

Add:

- entity mentions;
- entity profiles;
- chapter entity view;
- alias safety decisions;
- do-not-merge lists.

Use chapter-local context before global entity maps.

Recommended retrieval flow:

```text
question
  -> detect entities and aliases
  -> retrieve chapter_entity_view
  -> search Qdrant with book/chapter/entity filters
  -> expand to supporting ChapterFacts
  -> answer with citations
```

## Phase R3: Narrative GraphRAG

Add:

- relation facts;
- event facts;
- plot stages;
- entity states;
- relation states;
- event chains;
- Neo4j projection.

Graph expansion must retrieve more evidence; it must not become the final truth source.

Graph retrieval should be a context expansion layer:

```text
initial evidence
  -> related entity/relation/event nodes
  -> neighboring chapters or plot stages
  -> back to source chunks and ChapterFacts
```

The answer must still cite source text or ChapterFact evidence.

## Retrieval Algorithms

No single retriever is enough for fiction.

Recommended stack:

| Layer | Purpose |
|---|---|
| lexical / BM25-style | exact names, titles, source phrases, rare terms |
| dense vector | semantic similarity and paraphrases |
| structured lookup | ChapterFact, entity, event, relation fields |
| RRF fusion | combine independently ranked lists |
| reranker later | improve final context order |

BM25 alone is too literal. Dense vectors alone can blur distinct entities with similar semantics. Hybrid retrieval is the default.

Future reranker options:

- Qwen3 reranker if available locally;
- DeepSeek review/rerank for high-value or ambiguous answers;
- lightweight local reranker for routine QA.

## Embedding & Index Notes

### Character Limit

Qwen3-Embedding-0.6B supports ~48K tokens. We cap content at **50,000 chars** for safety.

When a chunk exceeds 50K chars, it is split at approximately the halfway point, preferring natural boundaries (paragraph → sentence → line → word → LLM fallback). Split segments record `parent_chunk_id` + `split_index` in Qdrant payload for relationship tracking.

See `app/utils/text_splitter.py` for the implementation.

### GPU Memory

On a 24 GB RTX 3090, SentenceTransformer + llama-server coexist on GPU 1 (`cuda:1`), leaving only ~1-2 GB free for embedding computation. Practical constraints:

- `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` required to avoid memory fragmentation OOM
- Index batch size = 2 (not 5) to keep per-batch memory low
- Each large chunk (~48K chars) takes ~10-15s to embed on GPU

## Why Not Graph First

AI Reader experience shows that graph quality is limited by:

- canonical name errors;
- alias bridge pollution;
- generic mentions;
- relation over-generalization;
- chapter context loss.

ChapterFact and review are required before a graph can be trusted.
