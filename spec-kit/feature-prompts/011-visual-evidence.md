# Spec Kit input — Visual evidence and lazy enrichment

**Feature directory:** `011-visual-evidence`  
**Maps to:** Work Package 10 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Expose exact source images or page/slide crops by safe handle and optionally derive OCR or captions only when requested or policy-enabled, clearly separating source evidence from model interpretation.

## Mandatory outcomes

- Source asset/crop is retrievable through bounded handles.
- OCR and captions are labelled derived with provider/version/input hash.
- Cache hits avoid repeated model calls.
- Default remains off or local-only.
- Egress policy blocks unauthorized external providers.
- Context compiler can escalate from description to original visual evidence.

## Explicit non-goals

- No automatic chart correctness guarantee.
- No external provider enabled by default.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
