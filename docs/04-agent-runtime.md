# Agent Runtime

## Concept

NovelBridge agents are task roles, not model instances.

An agent may call deterministic tools, local models, API models, validators, stores, and retrieval systems. Every meaningful action must be traceable.

## Two-Agent Architecture

NovelBridge is split into two agent roles with fundamentally different design goals:

### 1. Preprocessing & RAG Builder Agent (local 9B, offline batch)

**Role**: Data preprocessing pipeline that builds structured novel knowledge.

**What it does**:
- Chapter splitting and chunking with smart truncation (>50K chars → ~50% split with natural boundary preference, parent_chunk_id tracking)
- Entity/relation/event extraction (local 9B, "宁多勿漏")
- Entity merging and alias resolution
- Evidence validation (19 条中文形态学规则)
- Genre-aware strategies (修仙 vs 现实小说命名差异)
- Vector indexing to Qdrant (BATCH_SIZE=2, PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True)
- Cross-chapter consistency checking (ProfileQualityChecker)
- ContextSummaryBuilder: per-chapter injection of previous summaries + entity dictionaries (= AI keeping "读书笔记")
- **Training data generation**: export ChapterFacts as JSONL for future fine-tuning of the local 9B model itself

**Design principles**:
- Structured extraction + Knowledge Graph, not GraphRAG-first
- LLM extraction = "看见" (recall-oriented, 宁多勿漏)
- Rule-based validation as hallucination filter
- Voting/aggregation for global consistency
- Model output = candidate data, never truth. Evidence + review decide acceptance.
- 85% automated, 15% left for user review/fine-tuning

**Constraints**:
- Embedding model: Qwen3-Embedding-0.6B, 1024-dim cosine, max 50K chars
- Batch size = 2 (GPU memory constraint on 24GB RTX 3090 with SentenceTransformer + llama-server coexisting)
- Must set `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` for large chunk embedding
- Runs offline, no real-time requirements

### 2. QA Agent (API model, online interactive)

**Future design direction**.

**Role**: Answer user questions about novels with retrieval-augmented generation.

**Design inspirations** (to be elaborated later):
- Reference: programming coding agent design patterns (tool-use, plan-execute-verify, self-correction)
- Agent memory: conversation history, per-book session state, user preferences
- Context constraints: budget-aware context window management, sliding window, summarization
- Prompt engineering: role definition, citation format, uncertainty expression, multi-hop reasoning
- Tool set: Qdrant vector search, structured fact retrieval, Neo4j graph query, full-text search, chapter content access
- Evidence-first: every claim must cite source text with excerpt
- Hybrid retrieval: lexical exact match + dense vector search + structured ChapterFact retrieval + fusion
- Evaluation: answer accuracy, citation precision, hallucination rate

**Not in scope for Stage 1**:
- Real-time QA
- Conversation memory
- Agent orchestration

## Required Trace Types

### AgentRun

One long task, such as:

- `BOOK_IMPORT`
- `BOOK_BUILD`
- `CHAPTER_FACT_BUILD`
- `QA_ANSWER`
- `REVIEW`
- `EVALUATION`

### AgentStep

One ordered step in a run:

- `DECODE_SOURCE`
- `SPLIT_CHAPTERS`
- `BUILD_CHUNKS`
- `PRE_SCAN`
- `EXTRACT_MENTIONS`
- `BUILD_CHAPTER_FACT`
- `VALIDATE_EVIDENCE`
- `INDEX_RETRIEVAL`
- `ANSWER_WITH_CITATIONS`

### ModelCall

One model request.

Must record:

- provider and model name;
- prompt name and revision;
- schema revision;
- temperature and max tokens;
- input text or artifact reference;
- output text or artifact reference;
- parse status;
- evidence status;
- retry count;
- duration;
- error type and message.

## Agent Roles

| Agent | Responsibility |
|---|---|
| Orchestrator | schedule steps, persist state, resume/retry |
| Overview Agent | DeepSeek book prior and strategy hints |
| Preprocess Agent | cleanup, split, chunk, candidate hints |
| Extraction Agent | local 9B chunk mentions |
| ChapterFact Agent | aggregate mentions into ChapterFact |
| Validation Agent | schema and evidence validation |
| Review Agent | DeepSeek review for risky cases |
| Retrieval Agent | assemble evidence context |
| QA Agent | answer with citations |
| Audit Agent | run evaluation and regression checks |

## ModelProvider Interface

Implement providers behind one interface:

```text
chat()
chat_json()
extract_structured()
review_output()
repair_json()
answer_with_citations()
```

Initial providers:

- `DeepSeekProvider`
- `LocalLlamaCppProvider`

Later:

- OpenAI-compatible generic provider
- Qwen cloud provider
- Claude/Gemini/MiniMax providers

## Failure Policy

- Per chunk/chapter failures must not crash the full book build.
- Failed steps write `error_type` and `error_message`.
- Retry must be bounded and visible.
- JSON repair cannot invent missing facts.
