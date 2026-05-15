# NovelBridge Agent Start

Use this file as the first entry point for a fresh coding agent.

## Read First

1. `.opencode/skills/vibe-learn/SKILL.md`
2. `.vtl/vtl-adapter.json`
3. `docs/learn/vtl-state.json`
4. `docs/learn/current-stage.md`
5. `docs/learn/project-skeleton.md`
6. `docs/learn/demo-plan.md`
7. `docs/learn/table-design-review.md`
8. `docs/learn/table-design.md`

Do not read old planning drafts unless the user explicitly asks; the project has been simplified around a demo-first loop.

## Current Direction

Build a small working NovelBridge demo first, then harden it.

The first useful product slice is:

```text
sample txt/md -> Book/Chapter/Chunk -> AgentRun/AgentStep -> minimal question -> ChatMessage/Citation
```

Do not start with a full 20-table implementation or a full frontend.

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

## Vibe-Learn Closing Checklist

After every demo cycle reaches Evidence/Verify, **do not consider it done** until the script confirms all items are GREEN.

```powershell
python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json
```

If any item is RED:
- **practice_markers**: Add `@VTL-PRACTICE` to methods with genuine learning value.
- **retro_log**: Update `docs/learn/retro-log.md` with bugs, agent drift, and decisions from this cycle.
- **playbook**: Update `docs/learn/personal-vibecoding-playbook.md` if a new reusable rule emerged.
- **feedback_log**: Log skill-level blockers in `docs/learn/vtl-feedback-log.md`.

See `.opencode/skills/vibe-learn/SKILL.md > Closing Checklist` for details.
