# Script Contract

Scripts exist to save tokens and reduce risky manual edits.

## Required Behavior

All scripts should support `--json` when practical and output:

```json
{
  "status": "success|warning|error",
  "summary": "...",
  "artifacts": [],
  "recommended_reads": [],
  "next_actions": [],
  "warnings": [],
  "stop_condition": null
}
```

## Token Rules

- Do not output long diffs by default.
- Output changed file lists, suspected endpoint changes, field changes, marker counts, and recommended reads.
- Let the agent read only recommended files.
- Prefer `--compact` for normal use.

## Safety Rules

- Writing scripts must support `--dry-run`.
- Practice generation must stop if the target has uncommitted changes.
- Unmarked code must never be replaced.
- Only the selected version may be transformed.
- Failed scripts should leave a clear stop condition.

## Project Adapters

If generic scanning is inaccurate, create project-local adapters under:

```text
.vtl/
  vtl-adapter.json
  scripts/
  adapter-notes.md
```

Do not mutate the global skill scripts for a single project.
