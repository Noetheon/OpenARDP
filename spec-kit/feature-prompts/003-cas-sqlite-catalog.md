# Spec Kit input — Content-addressed storage and SQLite catalog

**Feature directory:** `003-cas-sqlite-catalog`  
**Maps to:** Work Package 2 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Persist immutable content objects, documents, versions and jobs safely on one machine so repeated ingestion can reuse exact content and interrupted work cannot expose partial state.

## Mandatory outcomes

- Filesystem CAS uses SHA-256 paths and atomic writes.
- SQLite schema and migrations register documents, versions, objects and jobs.
- Concurrent duplicate writes converge on one valid object.
- Interrupted commits expose no partial logical version.
- Reachability analysis identifies unreferenced objects without deleting live data.
- Path traversal and malformed identity inputs are rejected.

## Explicit non-goals

- No parser beyond test doubles.
- No automatic garbage deletion in the first slice.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
