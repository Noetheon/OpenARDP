# Spec Kit input — Portable ARDP package

**Feature directory:** `012-portable-ardp-package`  
**Maps to:** Work Package 11 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Export a self-describing, integrity-verifiable OpenARDP package and import it safely into another compatible local installation without trusting archive paths or unsupported schema versions.

## Mandatory outcomes

- Package manifest lists logical records, hashes and schema versions.
- Export is deterministic where declared.
- Import verifies every referenced object before commit.
- Byte corruption is detected.
- Path traversal, unsafe links and archive bombs are rejected.
- Unsupported major version is rejected.
- Imported package produces equivalent logical records.

## Explicit non-goals

- No executable code inside packages.
- No package signature PKI in MVP unless separately specified.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
