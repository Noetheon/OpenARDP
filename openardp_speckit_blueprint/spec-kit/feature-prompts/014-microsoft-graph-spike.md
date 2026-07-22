# Spec Kit input — Microsoft Graph connector design spike

**Feature directory:** `014-microsoft-graph-spike`  
**Maps to:** Work Package 13 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Validate a least-privilege OneDrive/SharePoint change-detection design with mocked notifications and delta queries, without requesting broad production access or deploying a live enterprise connector.

## Mandatory outcomes

- Connector port separates source events from ingestion.
- Webhook is treated only as a wake-up signal.
- Delta link and cursor state persist atomically.
- Missed notification, deletion, move and permission-change cases are modeled.
- Permission analysis documents least-privilege alternatives.
- Deployment and threat ADR is produced.

## Explicit non-goals

- No production tenant permissions.
- No live enterprise deployment.
- No assumption that webhook delivery alone is complete.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
