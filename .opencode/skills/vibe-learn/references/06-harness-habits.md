# Harness Habits

Teach harness engineering as practical vibe coding habits, not theory.

## Beginner Habits

During each stage, reinforce:

- define the stage boundary before coding
- say what is not in scope
- ask the agent which files it expects to touch
- require evidence before accepting "done"
- update field traces after API or DTO/VO changes
- record agent drift as a future prompt rule
- keep context compact and persistent in project docs

## Personal Playbook

Update `personal-vibecoding-playbook.md` at version checkpoints, repeated mistakes, or project end.

Use evidence-backed rules:

```text
Rule: When changing a backend API, also check frontend API calls.
Evidence: Stage v1-auth failed once because auth.ts still used the old field.
Confidence: high
Applies when: endpoint path, request body, response body, DTO, or VO changes.
```

## Drift Handling

Classify new requests:

- `keep`: belongs in the current stage.
- `defer`: valuable but should move to a later stage.
- `reject`: too heavy or not useful for this beginner project.

Always give the smallest next step the learner can still build and understand.
