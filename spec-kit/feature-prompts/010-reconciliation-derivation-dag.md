# Spec Kit input — Block reconciliation and derivation DAG

**Feature directory:** `010-reconciliation-derivation-dag`  
**Maps to:** Work Package 9 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Reuse unchanged normalized blocks and their derived caches after small document edits while invalidating only artifacts whose recorded inputs actually changed.

## Mandatory outcomes

- Matching algorithm and version are recorded.
- One paragraph edit preserves unrelated stable identities when confidence is sufficient.
- Low-confidence matches do not reuse derived data.
- Derivations record exact input hashes and dependencies.
- Changed table invalidates dependent summaries but not unrelated artifacts.
- Reconciliation decisions are testable and auditable.

## Explicit non-goals

- No claim of perfect stable identity across arbitrary reformatting.
- No mandatory embeddings.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
