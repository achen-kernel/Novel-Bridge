# AI Reader Lessons

Source materials:

- `AI Reader README.md`
- `AI Reader-1.pdf`
- `AI Reader-2.pdf`

We use these for product and engineering lessons only. Do not copy code from AI Reader V2.

## Product Lessons

- Users want to upload a novel and see chapters, graph, timeline, encyclopedia, reading highlights, and QA.
- Product coherence depends on PRD, UX, architecture, and acceptance criteria before coding.
- Long novels must be processed chapter by chapter, with retry and progress.
- ChapterFact-style intermediate data is more valuable than immediate global aggregation.

## Engineering Lessons

- Entity pre-scan improves extraction quality.
- Local small models are useful but rough; API models are more accurate.
- Context budget and timeout should adapt to model/provider.
- Desktop/local storage is useful, but NovelBridge targets a Java product API plus Python worker architecture.

## Quality Lessons

The biggest failures were not missing features; they were data quality failures:

- canonical name selection picked low-frequency formal names;
- Union-Find merged similar names;
- shared titles bridged unrelated characters;
- global alias maps polluted unrelated chapters;
- relation frequency voting chose generic relations over specific ones.

## Adopted Rules

- Use data-driven evaluation, not visual impression.
- Diagnose before fixing.
- Split problems by layer: canonical name, merge safety, highlighting, relation aggregation.
- Use quantified acceptance criteria.
- Keep regression tests for classic books.

## Core Philosophy (from AI Reader)

AI Reader's design philosophy, which NovelBridge adopts:

> 我们没有让 AI 直接"理解"文学，而是设计了一套结构化的验证管线：
> 1. LLM 提取只负责"看见"（宁多勿漏）
> 2. FactValidator 用 19 条中文地名形态学规则过滤幻觉
> 3. Genre-aware 策略让系统"知道"修仙和现实小说的命名差异
> 4. 最终由 ProfileQualityChecker 在聚合层做跨章节一致性校验

> 关于伏笔和长上下文注意力问题，我们通过 ContextSummaryBuilder 在每章提取时注入前序摘要+实体字典，相当于给 AI 一个"读书笔记"。确实无法完美，但把 85% 做到自动化、15% 留给用户微调，这个平衡点我们认为已经跨过了可用性阈值。

> 底层不是 GraphRAG 路线。GraphRAG 侧重"检索增强生成"，AI Reader 侧重"结构化提取+可视化"——每章提取 ChapterFact（人物/地点/关系/事件），再通过投票系统聚合成全书知识图谱。更接近 Information Extraction + Knowledge Graph 的思路。

## Design Decisions Derived From AI Reader

| Lesson | NovelBridge Decision |
|--------|---------------------|
| Entity pre-scan improves extraction quality | CandidateGenerator runs before extraction |
| Local small models are useful but rough | Local 9B for bulk draft, DeepSeek API for audit/review/prior |
| Canonical name selection picks wrong names | Use frequency + evidence-based voting, not arbitrary selection |
| Union-Find merges similar names wrongly | Chapter-aware alias views, not global alias maps |
| Relation frequency votes generic over specific | Use quality-weighted voting, not raw frequency |
| Long novels must process chapter-by-chapter | Chapter-at-a-time with retry and progress tracking |
| ChapterFact intermediate data > immediate global graph | Fact → validate → aggregate → project (never graph-first) |
| Context budget adapts to model/provider | Timeout and max_tokens configurable per provider |

## Differences From AI Reader

NovelBridge should differ in these ways:

- Java product API plus Python worker rather than Python-only backend.
- Relational source-of-truth first.
- Graph is a projection, not the first source of truth.
- DeepSeek handles audit/prior; local 9B handles bulk draft work.
- Quality harness is a first-class project artifact from Stage 0.
- Training data generation: pipeline exports ChapterFacts as JSONL for self-fine-tuning.
- Two-agent architecture: Preprocessing Agent (offline batch, local 9B) vs QA Agent (online interactive, API model).
