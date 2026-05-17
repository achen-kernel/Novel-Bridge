---
name: vibe-learn_remote
description: Demo-first learning harness for vibe coding. Use when a beginner or junior developer is building a Java/Spring Boot, Vue, MySQL, Redis, Python service, local LLM, or similar project with an AI coding agent and wants small verifiable demos, staged hardening, compact learning docs, project-structure adapters, scope control, bug/agent retros, optional Java/Python practice snapshots, and a personal AI coding playbook.
---

# Vibe Learn

Use this skill as a low-token companion harness for project learning through AI-assisted development, with Java/Spring Boot as the main backend lane and Python as an explicit growth lane when the project uses scripts, data pipelines, `rag-agent`, model calls, or service orchestration.

The default path is **demo first, then harden, then practice**. Do not expose several "modes" to the user unless they ask. A normal project loop already starts with a small demo and expands it.

## Core Role

Guide the agent to:

- Build a thin working demo before broad architecture work.
- Keep normal development on `main` or the user's regular branch.
- Keep learning state in compact project docs, not in long chat history.
- Explain only the current learning point, current risk, and next action.
- Preserve a clear line between shipped code, mock code, deferred work, and practice code.
- Convert bugs, agent drift, scope creep, and learner weak spots into reusable prompts and habits.
- Use suitable Python work as learning material when the project naturally includes Python services, deployment scripts, data processing, LLM calls, evaluation, or automation.

## Default Loop

Use one loop:

1. **Status**: run `scripts/vtl_status.py --json`; if state is missing, create `docs/learn_remote/vtl-state.json`.
2. **Structure**: run `scripts/vtl_scan.py --json`; if the scan is wrong, create or update `.vtl/vtl-adapter.json`.
3. **Readiness**: check that the next step can become a small working demo.
4. **Demo slice**: implement one end-to-end path with explicit mocks or shortcuts.
5. **Evidence**: verify with build/test/API/page/manual evidence before calling it done.
6. **Harden**: replace mocks, add validation, persistence, errors, tests, and cleaner boundaries.
7. **Practice decision**: either mark valuable complete Java/Python code with `@VTL-PRACTICE` or record why practice is skipped for this cycle.
8. **Retro**: record bugs, agent drift, design changes, and skill improvement candidates.

## Default Project Docs

Read only these by default:

- `docs/learn_remote/vtl-state.json`: machine-readable low-token state.
- `docs/learn_remote/current-stage.md`: active stage, demo slice, evidence, risks.

Read these only when the event requires it:

- `docs/learn_remote/project-skeleton.md`: recommended layered architecture template.
- `docs/learn_remote/learning-plan.md`: stage list and checkpoints.
- `docs/learn_remote/demo-plan.md`: walking skeleton and mock/debt list.
- `docs/learn_remote/flow-map.md`: backend flow, API contract, full-stack field trace.
- `docs/learn_remote/practice-plan.md`: practice versions and `@VTL-PRACTICE` candidates.
- `docs/learn_remote/retro-log.md`: bugs, agent drift, requirement decisions.
- `docs/learn_remote/personal-vibecoding-playbook.md`: user's reusable AI coding habits.
- `docs/learn_remote/vtl-feedback-log.md`: feedback for improving this skill.

If `practice-plan.md` or `personal-vibecoding-playbook.md` is missing, create it at the first stage close, first practice snapshot, or first user request for growth retrospection.

### Personal Notes Convention

Project-specific server setup pitfalls, environment config records, deployment troubleshooting, and user-specific playbook entries should go in `docs/personal-notes/`, **not** in `docs/learn_remote/`.

Rationale:
- `docs/learn_remote/` is for reusable learning artifacts (retros, practice plans, flow maps).
- `docs/personal-notes/` is for machine-specific or deployment-specific history that would confuse new agents if read by default.

When a project uses this directory, the orchestrator's `AGENTS.md` should reference it in a hard rule so new agents know to read it before performing server operations.

## Scope Slicing Rule

When a demo includes several independent concerns, split it before implementation.

Split especially when one stage includes two or more of:

- remote deployment or service startup
- database schema changes
- model inference or prompt/grammar work
- graph/vector/search infrastructure
- frontend review UI
- online QA
- fine-tuning or evaluation

Name slices explicitly, such as `demo-5a-remote-foundation`, `demo-5b-entity-extraction`, `demo-6-graph-hardening`, and `demo-7-graphrag-qa`.

Do not let the agent implement a full platform just because the requirement document describes the final system.

## Project Structure Adapter

Do not assume the repository root is the backend root.

Prefer `.vtl/vtl-adapter.json` when present. Otherwise, discover service roots recursively:

- Maven or Gradle backend: `pom.xml`, `build.gradle`, `build.gradle.kts`
- Vue or frontend: `package.json` with `vue`, `vite`, or frontend folders
- Python service: `pyproject.toml`, `requirements.txt`, `app/`, `src/`

If scripts mis-detect the structure, update the adapter first. Do not rewrite the project to fit the script.

## Python Learning Lane

When the project includes Python, treat it as a first-class learning track, not just glue code.

Use Python learning opportunities when they are already part of the current demo slice:

- `rag-agent` endpoints, request/response models, health checks, and service boundaries
- text chunking, extraction, validation, review queues, and dataset export
- LLM client code, prompt/grammar calls, retry/error handling, and structured output parsing
- Chroma or vector-index persistence and retrieval code
- deployment or orchestration scripts that are safer in Python than shell
- evaluation scripts, fixtures, and small reproducible test harnesses

Do not invent unrelated Python exercises. The best Python practice comes from verified project code that the learner needs to understand or maintain.

For Python practice candidates, prefer functions/classes with real learning value:

- parsing and validation logic
- typed request/response schemas
- service boundary code
- database/vector-store access
- deterministic extraction or normalization steps
- tests that demonstrate edge cases

Avoid turning environment setup, one-off shell wrappers, or trivial FastAPI boilerplate into practice unless the learner specifically asks.

When a cycle contains meaningful Python work, the retro should include one concise Python learning note: what concept was practiced, where the code lives, and what to revisit later.

## Skill Evolution

Do not edit this skill automatically during ordinary coding.

During project work, write improvement candidates to `docs/learn_remote/vtl-feedback-log.md`. Only revise the skill when the user explicitly asks for a skill iteration or when a repeated failure blocks progress.

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
   - `@VTL-PRACTICE` markers on code with genuine learning value, or a documented practice skip reason
   - `docs/learn_remote/retro-log.md` update with bugs, agent drift, decisions
   - `docs/learn_remote/personal-vibecoding-playbook.md` update
   - `docs/learn_remote/vtl-feedback-log.md` update for skill-level blockers

2. A command reference to the closing script:
   ```powershell
   python .opencode\skills\vibe-learn_remote\scripts\vtl_closing.py --root . --json
   ```

### Hook script (token optimization)

The `scripts/vtl_closing.py` script automates checklist verification:

```bash
python .opencode\skills\vibe-learn_remote\scripts\vtl_closing.py --root . --json
```

**Why a script instead of text-only?**
- Agent reading 4 bullet items + reasoning ~= 200–300 tokens
- Script output with status per item ~= 50 tokens
- Agent only acts on RED items, skips GREEN = significant token savings per cycle

The script checks:
1. `Practice decision` → scans `.java` files for `@VTL-PRACTICE`, or checks `practice-plan.md` for an explicit skip reason
2. `retro-log.md` → verifies existence and dated entry sections
3. `personal-vibecoding-playbook.md` → verifies existence
4. `vtl-feedback-log.md` → verifies existence (YELLOW if missing, not blocking)

The orchestrator agent runs this script after Evidence/Verify and fixes any RED result before declaring the stage closed. For infrastructure-only cycles, a documented practice skip is acceptable.

## Project structure convention (from project-skeleton.md)

> **Technology note**: The conventions below are Java / Spring Boot–specific (Maven, MyBatis, IntelliJ IDEA).
> For other stacks (Python, Node.js, Go, etc.), replace this section with the appropriate conventions.
> The core loop (Status → Demo → Evidence → Practice → Retro) and Closing Checklist are technology-agnostic.

Projects using this skill with Java/Spring Boot should follow a **common / pojo / server** three-layer package layout (参考苍穹外卖):

```
com.achen.novelbridge/
├── common/          ← 基础设施层（工具/异常/响应/枚举/配置）
├── pojo/            ← 数据模型层（DTO/Entity/VO）
└── server/          ← 业务主模块（controller/mapper/service/handler）
```

Detailed conventions:

- `common/result/Result<T>` — unified API response with `code` + `msg` + `data`
- `common/exception/BaseException` — business exception base class
- `server/handler/GlobalExceptionHandler` — `@RestControllerAdvice` catching all exceptions
- `common/properties/*Properties` — `@ConfigurationProperties` mapping application.yml config
- `common/util/*` — stateless utility classes with static methods

### ORM convention: MyBatis (not JPA)

Projects should use **MyBatis** for data access (not Spring Data JPA):

- Each mapper interface in `server/mapper/` package, annotated with `@Mapper`
- Simple CRUD via `@Insert`, `@Select`, `@Update`, `@Delete` annotations
- Complex queries in XML files under `resources/mapper/`
- `@MapperScan("com.achen.novelbridge.server.mapper")` on `@SpringBootApplication`
- Schema managed via `schema.sql` + `spring.sql.init.mode=always`
- Entity classes are plain POJOs with no ORM annotations
- Base entity fields (id, createdAt, updatedAt) handled by SQL DEFAULT

> **Upgrade path**: MyBatis → MyBatis-Plus when dynamic queries or pagination become complex. Both can coexist with careful configuration.

These are documented in detail in `docs/learn_remote/project-skeleton.md` (read-only recommended doc).

## Practice Marker Rule

Only code marked with `@VTL-PRACTICE` may be converted to TODO practice.

Practice is optional for infrastructure, deployment, planning, or prompt-only cycles. In those cases, record a skip reason in `docs/learn_remote/practice-plan.md` instead of forcing weak practice markers.

Prefer methods or functions with real learning value: business branching, database access, DTO/VO conversion, validation, exception handling, transaction logic, full-stack field mapping, typed Python schemas, service calls, parsing, chunking, extraction, vector-store access, or evaluation harness logic.

Avoid getters, setters, trivial wrappers, pure utilities, generated code, simple FastAPI route shells, environment boilerplate, or code the learner cannot reasonably complete from the current stage.

## Practice Snapshots And Growth Assets

- Keep complete working code on the main development branch.
- Generate practice snapshots only from complete code that has already been verified.
- Before generating practice code, run `scripts/vtl_practice.py --version <version> --dry-run --json`.
- Replace only code blocks marked with `@VTL-PRACTICE`; never replace unmarked code.
- Prefer a separate worktree or practice branch for learning snapshots.
- Record every practice version in `docs/learn_remote/practice-plan.md`.
- Update `docs/learn_remote/personal-vibecoding-playbook.md` after repeated mistakes, important checkpoints, or project completion.

### Recommended practice workflow (practice branch)

One `practice` branch, no sub-branches.

```bash
# First time (from the main project):
git branch practice
git worktree add ../Novel-Bridge-practice practice
```

**Open in IDEA** — IDEA creates `.idea/`, detects `pom.xml`, imports Maven. One-time.

**Generate practice TODO stubs:**
```bash
cd ../Novel-Bridge-practice
python <main-project>/.opencode/skills/vibe-learn_remote/scripts/vtl_practice.py \
  --version <version> \
  --target . \
  --inplace --skip-clean-check --json
```

**Write practice code, then commit with a descriptive message:**
```bash
cd ../Novel-Bridge-practice
git add -A
git commit -m "practice: chineseToInt 算法练习"
git push origin practice
```

### IDE support for practice snapshots

> **Technology note**: The configuration below is for IntelliJ IDEA + Java. For other stacks, generate the IDE/project
> configuration appropriate to that stack (e.g., `.vscode/launch.json` for VS Code, `pyproject.toml` for Python).

When the practice snapshot is used with IntelliJ IDEA (for writing TODO code), generate IDEA project configuration so the IDE indexes files and scans TODOs:

1. Create `.idea/misc.xml` — set `project-jdk-name="21"` and `languageLevel="JDK_21"`
2. Create `.idea/modules.xml` — reference the module `.iml` file
3. Create `.idea/modules/<module>.iml` — define source roots (src/main/java, src/main/resources, src/test/java)
4. Create `.idea/compiler.xml` — enable annotation processing for Lombok
5. Create `.idea/vcs.xml` — disable VCS

Without these files, IDEA does not index the practice directory and TODO scanning does not work.

The orchestrator agent should generate these files after calling `vtl_practice.py` when the practice target is intended for IDE use.

## Output Discipline

- Be concise.
- State what is demo, mock, debt, and verified.
- Do not generate large tutorials unless asked.
- Do not rewrite all learning docs after every code change.
- Use script summaries and recommended reads before opening broad diffs.
- Require evidence before marking a stage closed.
