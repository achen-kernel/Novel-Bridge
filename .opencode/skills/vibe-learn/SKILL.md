---
name: vibe-learn
description: Demo-first learning harness for vibe coding. Use when a beginner or junior developer is building a Java/Spring Boot, Vue, MySQL, Redis, or similar project with an AI coding agent and wants a small working demo first, then staged hardening, compact learning docs, project-structure adapters, practice TODO snapshots, bug/agent retros, and a personal AI coding playbook.
---

# Vibe Learn

Use this skill as a low-token companion harness for Java project learning through AI-assisted development.

The default path is **demo first, then harden, then practice**. Do not expose several "modes" to the user unless they ask. A normal project loop already starts with a small demo and expands it.

## Core Role

Guide the agent to:

- Build a thin working demo before broad architecture work.
- Keep normal development on `main` or the user's regular branch.
- Keep learning state in compact project docs, not in long chat history.
- Explain only the current learning point, current risk, and next action.
- Preserve a clear line between shipped code, mock code, deferred work, and practice code.
- Convert bugs, agent drift, and learner weak spots into reusable prompts and habits.

## Default Loop

Use one loop:

1. **Status**: run `scripts/vtl_status.py --json`; if state is missing, create `docs/learn/vtl-state.json`.
2. **Structure**: run `scripts/vtl_scan.py --json`; if the scan is wrong, create or update `.vtl/vtl-adapter.json`.
3. **Readiness**: check that the next step can become a small working demo.
4. **Demo slice**: implement one end-to-end path with explicit mocks or shortcuts.
5. **Evidence**: verify with build/test/API/page/manual evidence before calling it done.
6. **Harden**: replace mocks, add validation, persistence, errors, tests, and cleaner boundaries.
7. **Practice**: mark valuable complete code with `@VTL-PRACTICE`; generate snapshots only on request or checkpoint.
8. **Retro**: record bugs, agent drift, design changes, and skill improvement candidates.

## Default Project Docs

Read only these by default:

- `docs/learn/vtl-state.json`: machine-readable low-token state.
- `docs/learn/current-stage.md`: active stage, demo slice, evidence, risks.

Read these only when the event requires it:

- `docs/learn/project-skeleton.md`: recommended layered architecture template.
- `docs/learn/learning-plan.md`: stage list and checkpoints.
- `docs/learn/demo-plan.md`: walking skeleton and mock/debt list.
- `docs/learn/flow-map.md`: backend flow, API contract, full-stack field trace.
- `docs/learn/practice-plan.md`: practice versions and `@VTL-PRACTICE` candidates.
- `docs/learn/retro-log.md`: bugs, agent drift, requirement decisions.
- `docs/learn/personal-vibecoding-playbook.md`: user's reusable AI coding habits.
- `docs/learn/vtl-feedback-log.md`: feedback for improving this skill.

If `practice-plan.md` or `personal-vibecoding-playbook.md` is missing, create it at the first stage close, first practice snapshot, or first user request for growth retrospection.

## Project Structure Adapter

Do not assume the repository root is the backend root.

Prefer `.vtl/vtl-adapter.json` when present. Otherwise, discover service roots recursively:

- Maven or Gradle backend: `pom.xml`, `build.gradle`, `build.gradle.kts`
- Vue or frontend: `package.json` with `vue`, `vite`, or frontend folders
- Python service: `pyproject.toml`, `requirements.txt`, `app/`, `src/`

If scripts mis-detect the structure, update the adapter first. Do not rewrite the project to fit the script.

## Skill Evolution

Do not edit this skill automatically during ordinary coding.

During project work, write improvement candidates to `docs/learn/vtl-feedback-log.md`. Only revise the skill when the user explicitly asks for a skill iteration or when a repeated failure blocks progress.

Keep skill-facing instructions in English for portability across models. Answer the learner in their language.

## Reference Routing

- Demo-first development: read `references/08-demo-first-loop.md`.
- Project plan readiness: read `references/02-learning-readiness.md`.
- Stage start, close, and evidence checks: read `references/03-stage-harness.md`.
- Backend-to-fullstack flow or field mapping: read `references/04-backend-to-fullstack.md`.
- Practice branch, worktree, and TODO markers: read `references/05-practice-branch.md`.
- Personal habits and harness habits: read `references/06-harness-habits.md`.
- Script behavior or output contract: read `references/07-script-contract.md`.
- Skill evolution rules: read `references/09-skill-evolution.md`.
- Overall operating model: read `references/01-operating-model.md` only when changing the workflow.

## Closing Checklist (orchestrator integration)

When an orchestrator agent uses this skill through a project-level `AGENTS.md`, add these steps after each demo cycle to prevent skipping Practice and Retro.

### Project setup

The project's `AGENTS.md` should contain:

1. A `Vibe-Learn Closing Checklist` section with these items:
   - `@VTL-PRACTICE` markers on code with genuine learning value
   - `docs/learn/retro-log.md` update with bugs, agent drift, decisions
   - `docs/learn/personal-vibecoding-playbook.md` update
   - `docs/learn/vtl-feedback-log.md` update for skill-level blockers

2. A command reference to the closing script:
   ```powershell
   python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json
   ```

### Hook script (token optimization)

The `scripts/vtl_closing.py` script automates checklist verification:

```bash
python .opencode\skills\vibe-learn\scripts\vtl_closing.py --root . --json
```

**Why a script instead of text-only?**
- Agent reading 4 bullet items + reasoning ~= 200–300 tokens
- Script output with status per item ~= 50 tokens
- Agent only acts on RED items, skips GREEN = significant token savings per cycle

The script checks:
1. `@VTL-PRACTICE markers` → scans `.java` files in backend root
2. `retro-log.md` → verifies existence and dated entry sections
3. `personal-vibecoding-playbook.md` → verifies existence
4. `vtl-feedback-log.md` → verifies existence (YELLOW if missing, not blocking)

The orchestrator agent runs this script after Evidence/Verify and fixes any RED result before declaring the stage closed.

## Common module conventions (from project-skeleton.md)

Projects using this skill should adopt these common-module conventions:

- `common/result/Result<T>` — unified API response with `code` + `msg` + `data`
- `common/exception/BaseException` — business exception base class
- `common/handler/GlobalExceptionHandler` — `@RestControllerAdvice` catching all exceptions
- `common/properties/*Properties` — `@ConfigurationProperties` mapping application.yml config
- `common/util/*` — stateless utility classes with static methods

These are documented in detail in `docs/learn/project-skeleton.md` (read-only recommended doc).

## Practice Marker Rule

Only code marked with `@VTL-PRACTICE` may be converted to TODO practice.

Prefer methods with real learning value: business branching, database access, DTO/VO conversion, validation, exception handling, transaction logic, or full-stack field mapping.

Avoid getters, setters, trivial wrappers, pure utilities, generated code, or code the learner cannot reasonably complete from the current stage.

## Practice Snapshots And Growth Assets

- Keep complete working code on the main development branch.
- Generate practice snapshots only from complete code that has already been verified.
- Before generating practice code, run `scripts/vtl_practice.py --version <version> --dry-run --json`.
- Replace only code blocks marked with `@VTL-PRACTICE`; never replace unmarked code.
- Prefer a separate worktree or practice branch for learning snapshots.
- Record every practice version in `docs/learn/practice-plan.md`.
- Update `docs/learn/personal-vibecoding-playbook.md` after repeated mistakes, important checkpoints, or project completion.

## Output Discipline

- Be concise.
- State what is demo, mock, debt, and verified.
- Do not generate large tutorials unless asked.
- Do not rewrite all learning docs after every code change.
- Use script summaries and recommended reads before opening broad diffs.
- Require evidence before marking a stage closed.
