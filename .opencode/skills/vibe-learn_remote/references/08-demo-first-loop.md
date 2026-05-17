# Demo-First Loop

Use this reference when the project is early, the learner is uncertain, or the plan is becoming too broad.

## Principle

There is no separate "demo mode" the user must choose. The default development path is:

```text
small working demo -> evidence -> hardening -> practice snapshot -> retro
```

## Demo Slice Rules

- Pick one visible user path.
- Keep the slice end-to-end, even if some internals are mock or simplified.
- Mark every shortcut as `mock`, `temporary`, or `deferred`.
- Preserve the project's core design constraint even in the demo.
- Stop when the slice can be verified.

For a Java full-stack project, a good demo slice normally includes:

```text
UI or API entry -> Controller -> Service -> persistence or mock store -> response -> verification
```

For an AI/harness project, a good demo slice normally includes:

```text
input -> step state -> model/tool/mock result -> stored output -> evidence/citation -> verification
```

## Demo Exit Checklist

Before calling a demo slice done, record:

- What works.
- What is mocked.
- What is technical debt.
- How it was verified.
- What should be hardened next.

## Hardening Order

Harden in this order:

1. Replace fake persistence with real persistence.
2. Add status and error paths.
3. Add validation and idempotency rules.
4. Add tests or repeatable manual checks.
5. Clean boundaries and naming.
6. Add practice markers after the complete version works.

## Anti-Patterns

- Designing all tables before one path runs.
- Building a chat UI before citations or evidence exist.
- Adding a framework because it might be useful later.
- Calling mock behavior complete without recording the debt.
