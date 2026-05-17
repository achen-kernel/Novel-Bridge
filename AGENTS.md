# NovelBridge Agent Start

Use this file as the first entry point for a fresh coding agent.

## Read First

1. `.opencode/skills/vibe-learn/SKILL.md`
2. `.vtl/vtl-adapter.json`
3. `docs/learn/vtl-state.json`
4. `docs/learn/current-stage.md`
5. `docs/learn/project-skeleton.md`
6. `docs/learn/demo-plan.md`
7. `novel_bridge_demo_5_gbnf_开发需求文档_v_0_1.md`
8. `docs/learn/remote-server-structure.md`
9. `docs/learn/table-design-review.md`
10. `docs/learn/table-design.md`

Do not read old planning drafts unless the user explicitly asks; the project has been simplified around a demo-first loop.

Do not read files under `docs/private/` unless the user explicitly asks. That folder is ignored by git and is reserved for user-specific long-context handoff notes.

## Current Direction

Build a small working NovelBridge demo first, then harden it.

The project is now entering Demo 5, but Demo 5 is split to avoid scope creep:

```text
Demo 5A -> remote Linux service foundation
Demo 5B -> chunk + model_run + entity extraction candidate + review
Demo 6  -> relation/event/claim extraction and graph hardening
Demo 7  -> GraphRAG QA, evaluation, fine-tuning data preparation
```

Do not implement full GraphRAG, wiki alignment, relation/event/claim extraction, QA, and fine-tuning inside Demo 5A/5B.

## Repository Shape

- Backend root: `Novel-Bridge`
- Learning docs: `docs/learn`
- Project skill: `.opencode/skills/vibe-learn`
- Project adapter: `.vtl/vtl-adapter.json`

## Commands

```powershell
python .opencode\skills\vibe-learn\scripts\vtl_status.py --root . --json
python .opencode\skills\vibe-learn\scripts\vtl_scan.py --root . --json
cd Novel-Bridge
mvn -q test
```

## Hard Rules

- Keep demo slices small and verifiable.
- Mark mock or temporary behavior explicitly.
- Do not skip `AgentRun/AgentStep` for long-running build/query flows.
- Do not call question answering complete without `Citation`.
- Update `.vtl/vtl-adapter.json` when frontend or rag-service roots are created.
- Do not write server passwords, database passwords, Neo4j passwords, or API tokens into tracked files.
- Remote Linux deployment details belong in `.env`/local config; tracked docs may show host/user/port but not secrets.
- Server environment pitfalls, config records, and deployment-specific notes go in `docs/personal-notes/`. New agents doing server operations should read these before making changes.
- Project-specific records (`server-setup-pitfalls.md`, `personal-vibecoding-playbook.md`) are **not** standard vibe-learn docs — they belong in `docs/personal-notes/`, not `docs/learn/`.

## Vibe-Learn Closing Checklist

After every demo cycle reaches Evidence/Verify, **do not consider it done** until the script confirms all items are GREEN.

```powershell
python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json
```

If any item is RED:
- **practice_decision**: Add `@VTL-PRACTICE` to methods with genuine learning value, or document `SKIP-PRACTICE` in `docs/learn/practice-plan.md`.
- **retro_log**: Update `docs/learn/retro-log.md` with bugs, agent drift, and decisions from this cycle.
- **playbook**: Update `docs/learn/personal-vibecoding-playbook.md` if a new reusable rule emerged.
- **feedback_log**: Log skill-level blockers in `docs/learn/vtl-feedback-log.md`.

See `.opencode/skills/vibe-learn/SKILL.md > Closing Checklist` for details.
