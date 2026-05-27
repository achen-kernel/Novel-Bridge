# Quality Harness

## Purpose

Historical pitfalls must become checks, not just notes.

This document is the quality gate source for implementation stages.

## Encoding Gate

- Original bytes hash is stored.
- Detected/provided encoding is stored.
- Internal text is UTF-8.
- MySQL uses `utf8mb4`.
- GB18030/GBK input must not produce mojibake.

## Secret Gate

- No passwords, API keys, tokens, private keys, or real `.env` values in tracked files.
- `.env.example` uses placeholders only.

## Deployment Gate

Health checks must test behavior, not only ports:

- MySQL query succeeds.
- Neo4j auth and query succeed.
- llama-server returns `/v1/models`.
- rag-agent returns `/health`.
- required directories are writable.

## Model Output Gate

- JSON parse errors are recorded.
- Repair attempts are bounded.
- Per chunk/chapter failure does not crash the full book.
- `max_tokens` is high enough for expected schema.
- local Qwen/llama paths must account for reasoning output quirks.

## Retrieval Gate

- Qdrant is the default vector database.
- Embedding model defaults to `Qwen/Qwen3-Embedding-0.6B`, 1024 dimensions, cosine distance.
- Dense retrieval must be filterable by `book_id` and preferably `chapter_id`.
- Do not rely on dense retrieval alone for entity-heavy questions.
- Lexical retrieval must remain available for exact names, rare terms, chapter titles, and source phrases.
- Hybrid candidate fusion should use RRF or an explicitly documented scoring policy.
- Answers must cite source chunks or ChapterFact evidence, not just vector hits.

## Prompt Gate

- Prompt templates are versioned.
- Prompt variable rendering must not conflict with JSON braces.
- Prompt output schemas are recorded with schema revision.

## Evidence Gate

- Validate evidence with normalized matching before rejection.
- Do not rely only on strict exact substring matching.
- Store evidence level.
- Unsupported facts remain candidates or review items.

## Alias Gate

Default deny for global alias merges when:

- generic title or role;
- shared family/position label;
- similar names with different suffixes;
- low evidence;
- cross-chapter bridge with no direct identity proof.

## Highlight Gate

Reading highlights must use chapter/stage entity views, not global alias maps.

## Relation Gate

Specific relation beats generic relation when evidence supports it:

```text
sworn sibling > friend
master/apprentice > superior/subordinate
family relation > close relation
enemy pursuit > generic conflict
```

## Stage Close Gate

A stage is not done without:

- implemented scope summary;
- explicit out-of-scope notes;
- test/build/API/manual evidence;
- known risks;
- updated retro/playbook when a new reusable rule appears.
