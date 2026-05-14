# Skill Evolution

Use this reference only when the user asks to improve the skill or when repeated project failures show the skill is missing a rule.

## Default Policy

Do not edit the skill during ordinary feature work.

Ordinary work should update project learning assets:

- `docs/learn/retro-log.md`
- `docs/learn/personal-vibecoding-playbook.md`
- `docs/learn/vtl-feedback-log.md`

The skill should change only after evidence accumulates.

## Feedback Entry

Record improvement candidates like this:

```text
Date:
Project stage:
Symptom:
Why current skill did not help:
Proposed skill/script change:
Evidence:
Priority: low | medium | high
```

## When To Revise The Skill

Revise the skill when:

- A script repeatedly mis-detects common project structures.
- The agent repeatedly skips required evidence.
- The learner repeatedly asks the same process question.
- A project-specific rule has become generally reusable.

Do not revise the skill for a one-off preference or a single project quirk. Put those in `.vtl/vtl-adapter.json` or project docs.

## Revision Rules

- Keep `SKILL.md` short and stable.
- Put detailed variants in `references/`.
- Put deterministic behavior in `scripts/`.
- Prefer English for model-facing instructions.
- Keep learner-facing examples in the learner's language when useful.
- Test scripts after changing them.
- Validate the skill folder if a validator is available.

## Promotion Path

Use this path:

```text
project feedback -> project adapter or doc rule -> repeated evidence -> skill reference/script -> SKILL.md summary
```
