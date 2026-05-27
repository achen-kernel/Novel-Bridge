# current-stage.md

Stage id: `stage-6h-runtime-closure-fixes`
Status: `completed`
Loop: `stage-6-demo-prep`

## Goal

Fix the real runtime closure of Tool Orchestration + Memory + Planner + Audit.
The code had the structures (planner tool_sequence, ToolRegistry, ReAct loop, MemoryManager, answer_polish) but the wiring was incomplete at runtime.

## Scope

In:

- Fix #1: `/run` now consumes `planner.tool_sequence`. When no tool_sequence provided, it re-calls planner internally.
- Fix #2: `_default_sequence()` passes ALL ReaderRequest fields (target_name, target_type, analysis_type, trace_target_type, chapter_range, session_id, issue_type, target, evidence).
- Fix #3: `hybrid_search` items saved to `accumulated["search_items"]` and `L2 EvidenceMemory`.
- Fix #4: `audit` tool receives accumulated answer and writes polished answer back. Final answer always polished.
- Fix #5: `ToolExecutor.execute()` injected with `run_id`/`step_id` for trace continuity.
- Fix #6: Retrieval optimizations aligned: entity alias search, statistical queries, abstract query rewrite, empty-result fallback.
- Fix #7: Provider-specific prompts in `qa_runner.py`: Local 9B stricter, DeepSeek lighter.
- Fix #8: Documentation updated.

Out:

- Java facade (deferred).
- Graph-first trace visualization (deferred).
- KnowledgePatch merge (never auto).
- learn_style / authoring (contract-only).

## Evidence

- All 111 tests pass (no regression).
- `test_reader_agent_tools.py` — 15 tests, covers tool registry + ReAct think.
- `test_memory_layers.py` — 37 tests, L0/L1/L2 + MemoryManager.
- `test_answer_polish.py` — 23 tests, provider-aware + model audit.
- `test_session_memory.py` — 17 tests, session + reference resolution.
- `test_reader_agent_planner.py` — 18 tests, planner + tool_sequence.
- `test_agent_runtime_skeleton.py` — skeleton smoke test.

## Risks

| Risk | Status | Next |
|------|--------|------|
| ToolExecutor run_id may be None if mode runner doesn't create a run | accepted | all mode runners create runs via run_store |
| hybrid_search items → L2 uses heuristic EvidenceLevel.NEAR | intentional | can be refined per source type |
| ReAct think still requires DeepSeek provider | accepted | deterministic fallback when local provider |
