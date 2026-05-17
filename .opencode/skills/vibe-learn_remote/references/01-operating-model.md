# Operating Model

This skill is a build-from-zero learning harness, not a project manager, architecture course, or full observability system.

## Main Split

- Development plan: may come from the user, the base model, or a planning skill.
- Learning plan: created by this skill from the development plan.
- Development branch: `main` or the user's normal branch, always kept runnable.
- Practice branch/worktree: generated from `main`, with selected marked code converted to TODO practice.

## Default Loop

1. Check readiness of the plan.
2. Start one active stage.
3. Let the development agent build on `main`.
4. Use scripts to collect compact facts.
5. Explain only the current stage's learning points.
6. Record flow, practice, and retros only when events occur.
7. Generate practice snapshots at version checkpoints.
8. Update the personal playbook after repeated mistakes, major checkpoints, or project completion.

## Non-Goals

- Do not support existing-codebase onboarding as a first-class v0.1 mode.
- Do not teach broad software engineering theory ahead of need.
- Do not generate enterprise PRDs.
- Do not auto-score practice submissions in v0.1.
- Do not maintain a long-lived handwritten practice branch; regenerate stage snapshots from `main`.

## Token Budget

Default reads:

- `docs/learn_remote/vtl-state.json`
- `docs/learn_remote/current-stage.md`

On-demand reads:

- `learning-plan.md` for stage transitions.
- `flow-map.md` for API, DTO/VO, DB, or Vue field changes.
- `practice-plan.md` for markers and snapshots.
- `retro-log.md` for bugs, agent drift, or requirement decisions.
- `personal-vibecoding-playbook.md` for version checkpoints and final retros.
