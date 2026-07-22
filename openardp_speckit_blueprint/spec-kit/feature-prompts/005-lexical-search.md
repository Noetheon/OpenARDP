# Spec Kit input — Source-backed lexical search

**Feature directory:** `005-lexical-search`  
**Maps to:** Work Package 4 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Let an operator search prepared document blocks by exact terms and phrases and receive deterministic source-backed results without loading complete documents.

## Mandatory outcomes

- SQLite FTS5 indexes current logical versions.
- Exact term and phrase searches are tested.
- Results include document ID, exact version, block ID and source location.
- Superseded or deleted logical versions are excluded by default.
- Filters and ranking behavior are documented.

## Explicit non-goals

- No semantic/vector retrieval.
- No answer generation.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
