# Spec Kit input — Domain models and interchange schemas

**Feature directory:** `002-domain-models-schemas`  
**Maps to:** Work Package 1 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Define the canonical OpenARDP domain objects and public JSON contracts so independently implemented components can exchange manifests, blocks, derivations, relations and context bundles deterministically.

## Mandatory outcomes

- Pydantic v2 domain models enforce documented invariants.
- JSON Schema 2020-12 contracts validate golden fixtures.
- Canonical serialization produces deterministic SHA-256 identities across runs.
- Unsupported major schema versions fail clearly.
- Schema and model changes are traceable and tested.

## Explicit non-goals

- No persistence implementation.
- No document parsing or retrieval.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
