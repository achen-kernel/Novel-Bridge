# Learning Readiness Check

Use this before turning a generated project plan into a learning plan.

## Goal

Decide whether the plan is clear enough for a beginner to start learning while building. This is a lightweight gate, not a full design review.

## Checks

- Project goal is explainable in one or two sentences.
- MVP has 3-5 core features, or can be reduced to that.
- Each feature can map to page, API, service, data, and verification.
- The stack is not overloaded for a beginner.
- Each stage can produce runnable evidence.
- Each stage has 1-3 learning goals.
- Risky features are deferred: payment, multi-tenant auth, message queues, recommendation systems, complex permissions, microservices, advanced deployment.

## Output

Use one status:

- `Green`: start.
- `Yellow`: start after shrinking scope.
- `Red`: re-cut the MVP before coding.

Always include the smallest viable next version.

## Good Enough Standard

Do not block for missing enterprise-level artifacts. The plan is good enough when the agent can create a stage plan and the learner can explain what the next stage will build, verify, and practice.
