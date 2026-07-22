# Spec Kit input — Automatic local file watcher

**Feature directory:** `009-local-watcher`  
**Maps to:** Work Package 8 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Automatically schedule ingestion after a user saves a supported file in a watched directory, while coalescing noisy save events and never processing temporary Office lock files.

## Mandatory outcomes

- Watcher debounces bursts into one stable job.
- Stable snapshot checks avoid reading partially written files.
- Office temporary files such as ~$ are ignored.
- Persistent job states survive process restart.
- Deletion marks source state without deleting historical versions.
- Watcher reuses unchanged content.

## Explicit non-goals

- No OneDrive or SharePoint integration.
- No system-wide privileged daemon requirement.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
