# Spec Kit input — Text ingestion vertical slice

**Feature directory:** `004-text-ingestion-slice`  
**Maps to:** Work Package 3 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Allow an operator to initialize a local OpenARDP workspace and ingest TXT or Markdown files once. Re-ingesting an unchanged file must reuse the prior result rather than invoking the parser again.

## Mandatory outcomes

- CLI supports init, ingest, list, status, outline and get.
- TXT/MD parser produces source-backed blocks and document hierarchy.
- Unchanged SHA-256 source records a cache hit and skips parsing.
- Changed source creates a new immutable version.
- Original files are never modified.
- Every block identifies exact source version and location.

## Explicit non-goals

- No PDF, DOCX or PPTX support.
- No embeddings, MCP or watcher.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
