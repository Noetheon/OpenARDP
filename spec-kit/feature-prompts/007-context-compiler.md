# Spec Kit input — Budgeted context compiler

**Feature directory:** `007-context-compiler`  
**Maps to:** Work Package 6 in `docs/09_CODEX_EXECUTION_PLAN.md`

Use this document as the input to `$speckit-specify`. Read `AGENTS.md`, the constitution, relevant architecture docs and ADRs before creating the feature specification.

## User and outcome

Compile the smallest auditable evidence bundle needed for a task from prepared document versions, while respecting a declared context budget and reporting when unavailable visual evidence is required.

## Mandatory outcomes

- Compiler accepts query, document scope, exact version policy and budget.
- Lexical and structural expansion select evidence deterministically.
- Context bundle pins exact blocks and source versions.
- Budget is not exceeded beyond declared estimator tolerance.
- Numeric tasks include exact table/source evidence.
- Visual tasks explicitly request visual evidence instead of inventing detail.
- Selection rationale is auditable.

## Explicit non-goals

- No generative answer production.
- No vector retrieval requirement.

## Specification requirements

- Express behavior as prioritized, independently testable user/operator stories.
- Include Given/When/Then acceptance scenarios, negative cases and relevant security cases.
- Define measurable success criteria without inventing unsupported performance targets.
- Preserve all project-level constraints; flag ambiguity rather than silently changing architecture.
- Require tests for every public contract, security boundary and persisted behavior introduced by this feature.
- Keep later work packages outside this feature even if their abstractions appear convenient.
