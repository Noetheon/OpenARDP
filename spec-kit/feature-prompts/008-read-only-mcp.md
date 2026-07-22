# Spec Kit input — Read-only MCP access

**Feature directory:** `008-read-only-mcp`  
**Maps to:** Work Package 7 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Allow Codex and compatible agents to list prepared documents, inspect outlines, search, fetch blocks and compile context through a read-only MCP server without arbitrary filesystem access.

## Mandatory outcomes

- MCP SDK version is pinned within safe bounds.
- Tools expose list, document metadata, outline, search, block and context operations.
- Large results use safe resource/file handles.
- Callers cannot request arbitrary host paths.
- No side-effecting document mutation or external action tools exist.
- Prompt-injection fixture cannot trigger a side effect.

## Explicit non-goals

- No write MCP tools.
- No authentication or remote multi-user deployment.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
