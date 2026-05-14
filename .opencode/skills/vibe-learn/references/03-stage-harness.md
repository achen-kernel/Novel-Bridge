# Stage Harness

Use one active stage at a time.

## Stage Status

Allowed status values:

- `planned`
- `in_progress`
- `review`
- `closed`
- `snapshot`

Do not start a new stage until the current one is closed or explicitly paused.

## Current Stage Fields

Keep `current-stage.md` compact:

- stage id and version
- status
- feature goal
- not in scope
- likely files
- learning goals
- acceptance evidence
- backend/full-stack checkpoints
- practice candidates
- open risks

## Agent Contract

Before coding a stage, state:

- what to build
- what not to build
- likely files or modules
- required verification
- when to update `flow-map.md`
- when to add practice markers

## Close Criteria

A stage can close only when it has:

- functional evidence: build/test/API/page/manual check
- learning evidence: updated flow or stage notes
- practice evidence: marker candidates reviewed or explicitly skipped
- retro evidence: bug, drift, or decision recorded if it happened

If evidence is missing, set status to `review`, not `closed`.
