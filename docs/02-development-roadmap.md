# Development Roadmap

## Stage 0: Reboot Docs And Schema

In:

- product goal;
- architecture;
- data model;
- agent runtime;
- pipeline;
- RAG strategy;
- quality harness;
- deployment notes;
- revised vibe-learn harness direction.

Out:

- Java business implementation;
- Python implementation;
- model calls;
- remote deployment.

Evidence:

- docs exist and agree on the same core flow;
- v1 schema exists;
- AGENTS.md points new agents to the new route.

## Stage 1: Foundation Skeleton

Goal: rebuild project skeletons.

- Rewrite Java Spring Boot app with clean dependencies and config.
- Pin Java technology choices from `docs/10-java-tech-stack.md`.
- Keep Java baseline on JDK 21 + Spring Boot 4.0.6 unless a concrete incompatibility appears.
- Create Python `apps/rag-agent` FastAPI skeleton.
- Add health endpoints.
- Add DB migration/init path.
- Add Qdrant configuration placeholders and health-check stub.
- Add embedding configuration placeholders for `Qwen/Qwen3-Embedding-0.6B`.
- Add shared response/error conventions.

Done when Java and Python health checks run locally and test commands pass.

## Stage 2: Book Import And Text Processing

Goal: deterministic book ingestion.

- Upload TXT.
- Detect/decode encoding.
- Save book and source metadata.
- Split chapters.
- Build chunks.
- Record `AgentRun` and `AgentStep`.

Done when one test book imports, splits, chunks, and records trace rows.

## Stage 3: ChapterFact MVP

Goal: create source-grounded ChapterFact drafts.

- Generate candidate hints with rules/NLP.
- Use local 9B or placeholder rules for first drafts.
- Store ChapterFact JSON and evidence records.
- Use DeepSeek for sampled review later in this stage.

Done when selected chapters have ChapterFacts with evidence and validation status.

## Stage 4: Evidence-First QA

Goal: answer questions with citations.

- Implement Evidence-first Hybrid RAG.
- Use Qdrant + `Qwen/Qwen3-Embedding-0.6B` for dense chunk retrieval.
- Add lexical retrieval fallback for exact names and source phrases.
- Fuse chunk and ChapterFact candidates.
- Build answer context.
- Generate answer with citations.
- Store chat messages and citation rows.

Done when a user asks a question and receives a grounded answer with source excerpts.

## Stage 5: Entity Governance

Goal: prevent AI Reader style alias failures.

- Entity mentions and profiles.
- Alias safety review.
- Generic mention blocklist.
- Do-not-merge rules.
- Chapter entity view for highlighting.

Done when chapter-level highlighting avoids global alias pollution.

## Stage 6: Narrative Graph

Goal: project reviewed facts into graph structures.

- Relation mentions and facts.
- Event mentions and facts.
- Plot stages.
- Entity and relation states.
- Neo4j projection.

Done when graph retrieval expands evidence without replacing source citations.

## Stage 7: Audit And Dataset

Goal: quality regression and training data.

- Evaluation cases.
- Evaluation runs and reports.
- Bug pattern tracking.
- Dataset export after review.
- 9B fine-tuning becomes a downstream enhancement.
