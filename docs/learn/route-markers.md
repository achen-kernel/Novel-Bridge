# Route Markers

Route markers identify important code paths for future agents and human review.

They are not practice markers and should be used sparingly.

## Marker Types

| Marker | Meaning |
|---|---|
| `@NB-ENTRYPOINT` | Main API/service entrypoint |
| `@NB-AGENT-STEP` | Long-running agent step boundary |
| `@NB-MODEL-CALL` | Model provider call boundary |
| `@NB-EVIDENCE` | Evidence validation or citation logic |
| `@NB-DATA-WRITE` | Important database write |
| `@NB-RISK` | Code tied to a known historical pitfall |
| `@NB-ROADMAP` | Deliberate extension point |

## Rules

- Mark only important routes.
- Include a short reason near the marker.
- Do not mark trivial getters, setters, wrappers, generated code, or every helper.
- When a marker points to a historical pitfall, reference the relevant doc.

## Current Important Routes

Stage 0 has no production code routes yet.

Expected first routes in Stage 1:

- Java application entrypoint.
- Python rag-agent `/health`.
- database schema initialization.
- model provider interface.
- ingestion encoding utility.
