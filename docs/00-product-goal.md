# NovelBridge Product Goal

## Definition

NovelBridge is an API-first novel reading and authoring analysis agent.

It reads long-form fiction in stages, calls models and deterministic tools, records what it did, validates evidence, and turns source text into traceable assets for reading, review, retrieval, graph analysis, and authoring support.

## What It Is

- A reading agent that processes books chapter by chapter.
- A knowledge engineering system that stores source-grounded ChapterFacts.
- A reviewable analysis workspace for entities, relationships, events, locations, items, and settings.
- A retrieval and citation system for grounded question answering.
- A future narrative graph and authoring assistant.

## What It Is Not

- Not a one-shot chatbot over a full novel.
- Not a training-data pipeline first.
- Not a graph database demo first.
- Not a local-model-only project.
- Not a system that trusts model memory over source evidence.

## Core User Scenarios

1. Import a novel and see its chapters/chunks processed reliably.
2. Ask questions and receive answers with original-text citations.
3. Inspect ChapterFacts: characters, events, relationships, locations, items, concepts, and evidence.
4. Review risky entities, aliases, and relationships before they become stable facts.
5. Explore a later narrative graph, timeline, character cards, and plot stages.
6. Export evaluated facts or training samples after audit.

## Success Criteria

The first usable version succeeds when:

- a TXT novel can be imported without mojibake;
- chapters and chunks are reproducible;
- ChapterFact drafts are stored with evidence records;
- QA answers include citations;
- task and model-call traces are queryable;
- failures are recorded per stage/chunk rather than crashing the whole build.

## Primary Constraint

Quality beats quantity. A small number of source-grounded, reviewable facts is better than a large noisy graph.
