# Spec Kit input — Repository baseline

**Feature directory:** `001-repository-baseline`  
**Maps to:** Work Package 0 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Create an independently verifiable engineering foundation for OpenARDP. A maintainer must be able to clone the repository, install the pinned Python environment, run all quality gates, and understand the contribution and security process without any document-ingestion feature being implemented.

## Mandatory outcomes

- Python 3.12 project managed by uv with committed lock file.
- Package layout follows AGENTS.md architecture boundaries.
- Ruff lint and format checks, strict mypy, pytest and coverage are configured.
- Pre-commit and least-privilege GitHub Actions CI are present.
- License, security, contribution and validation documentation are coherent.

## Explicit non-goals

- No document parser, database, MCP server, watcher or product behavior.
- No cloud service or external model integration.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
