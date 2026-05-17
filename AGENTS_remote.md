# NovelBridge Remote Agent Start

Use this file as the first entry point for the remote Linux development agent.

## Workspace Boundary

You are restricted to:

```text
/home/wk/novelbridge
```

Do not read or write outside this directory unless the user explicitly asks.

## Role

You are the remote-side implementation agent for NovelBridge AI services.

Your long-term ownership includes:

```text
apps/rag-agent/
deploy/remote/
remote service health checks
llama.cpp integration
book-source ingestion from remote MySQL
book structure analysis
chapter splitting
chunk generation
structured extraction runners
prompt / schema / grammar assets
model call tracing
candidate validation and review support
Neo4j graph writes
Chroma/vector integration
evaluation and data export helpers
```

The local Codex guidance agent handles architecture review and planning. You should implement only the explicitly requested remote development slice.

Current phase:

```text
Demo 5B: remote book decomposition + chunking + model_run + entity candidate + minimal review/graph write
```

Demo 5A remote service foundation is considered already connected locally and remotely by the user.

Later phases are expected, but do not jump ahead:

```text
Demo 6:
  relation / event / claim extraction
  entity merge and alias handling
  graph hardening and conflict checks
  stronger review workflows

Demo 7:
  GraphRAG QA
  retrieval evaluation
  citation verification
  fine-tuning data preparation/export
```

Implement only the current stage unless the user explicitly moves the project forward.

## Read First

1. `docs/learn_remote/remote-agent-instructions.md`
2. `docs/learn_remote/demo-5b-remote-data-flow.md`
3. `.opencode/skills/vibe-learn_remote/SKILL.md`
4. `.vtl/vtl-adapter.json`
5. `docs/learn_remote/vtl-state.json`
6. `docs/learn_remote/current-stage.md`
7. `docs/learn_remote/demo-plan.md`
8. `novel_bridge_demo_5_gbnf_开发需求文档_v_0_1.md`
9. `docs/learn_remote/remote-server-structure.md`
10. `docs/learn_remote/table-design-review.md`
11. `docs/learn_remote/table-design.md`

Do not read old planning drafts unless the user explicitly asks.

Do not read files under `docs/private/` unless the user explicitly asks. That folder is for user-specific long-context handoff notes and should not be required for ordinary remote implementation.

## Allowed Edit Areas

Prefer editing only:

```text
apps/rag-agent/
deploy/remote/
scripts/remote/
docs/learn_remote/
.opencode/skills/vibe-learn_remote/
.vtl/
```

Treat these as runtime or secret-bearing areas. Do not edit them unless explicitly requested:

```text
data/
logs/
runtime/
models/
env/
.env
```

## Development Direction

Build the remote AI service line in small, verifiable demo slices.

The current slice is Demo 5B. Finish the smallest working entity extraction loop first, then harden it.

For the current flow, local Java only uploads/registers the whole book into one remote MySQL book-source table and triggers the remote agent. The remote `rag-agent` owns downstream generated artifacts:

```text
book_source -> structure analysis -> chapter -> chunk -> model_run -> entity_candidate -> review -> entity_profile / minimal graph
```

The immediate target is not a general autonomous agent. Prefer deterministic, auditable workflow runners:

```text
book_source -> chapter -> chunk -> prompt -> llama.cpp -> parse -> validate -> model_run -> candidate -> review -> approved graph write
```

For future stages, keep the same principle:

```text
Demo 6 extraction runners:
  entity/relation/event/claim prompt -> model -> validate -> candidate -> review -> graph write

Demo 7 QA runners:
  retrieve -> expand graph -> build context -> answer -> citation validation -> trace
```

Do not implement full GraphRAG, wiki alignment, relation/event/claim extraction, QA, fine-tuning, or complex frontend workflows inside Demo 5B.

Do not introduce ReAct, LangGraph, LangChain, or long-term chatbot-style memory by default. If agentic planning becomes useful later, add it behind a narrow runner boundary with trace records and explicit user approval.

## Remote Service Commands

```bash
cd /home/wk/novelbridge/deploy/remote
bash nb_status.sh
bash nb_healthcheck.sh --json
```

Check `rag-agent`:

```bash
curl http://127.0.0.1:18081/health
```

Check native `llama-server`:

```bash
curl http://127.0.0.1:18080/v1/models
```

Use `/v1/models` for llama.cpp availability. Do not rely only on `/health`.

## Hard Rules

- Keep demo slices small and verifiable.
- Mark mock or temporary behavior explicitly.
- Local Java writes only the remote book-source upload table for this flow.
- Remote rag-agent owns chapter splitting, chunking, model extraction, validation, candidate generation, and optional graph/vector writes.
- Do not skip `AgentRun` / `AgentStep` for long-running build or extraction flows.
- Every model call must create a `ModelRun` or equivalent trace.
- Candidate extraction results are not final truth. They require review before approved graph writes.
- Do not call question answering complete without `Citation`.
- Do not write server passwords, database passwords, Neo4j passwords, API tokens, SSH keys, or real `.env` values into tracked files.
- Do not overwrite raw prompt/output/error records.

## Output Required After Each Slice

Report:

```text
Changed files
Implemented behavior
Mock/debt still present
Verification commands and results
Files that should be synced back to the local Windows repo
```

Do not claim Demo 5B complete unless the extraction loop has trace, candidate, review, and verification evidence.
