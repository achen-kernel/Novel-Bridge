# Practice Branch and Markers

Use normal development on `main` and generate practice from it.

## Branch Model

- `main`: complete runnable project.
- `practice`: generated learning branch or worktree.

Prefer worktree when possible:

```text
my-project/           main
my-project-practice/  practice
```

## Snapshot Rule

Practice snapshots are generated per version:

1. Finish the stage on `main`.
2. Ensure `main` has the complete runnable solution.
3. Check the practice target is clean.
4. Sync from `main`.
5. Replace only selected `@VTL-PRACTICE` blocks.
6. Record source commit and version.

## Marker Quality

Prefer marking code with at least one of:

- business branch
- validation or exception handling
- database access
- DTO/VO conversion
- transaction boundary
- full-stack field mapping

Avoid marking:

- getters/setters
- generated code
- trivial wrappers
- code requiring hidden context
- high-risk infrastructure code

## Marker Format

```java
// @VTL-PRACTICE version=v1-auth level=2 module=auth target=method
// name=login
// signature=public LoginVO login(LoginDTO loginDTO)
// goal=Complete login: query user, validate password, create token.
// prerequisites=Controller-Service-Mapper flow; DTO/VO; password hashing.
// inputs=LoginDTO username and password.
// outputs=LoginVO token and user display fields.
// pitfalls=null user; wrong password; inconsistent token response.
// hints=Find the user first, then validate password, then create the response.
public LoginVO login(LoginDTO loginDTO) {
    // complete implementation
}
```

Store marker rationale in `practice-plan.md`.
