# Documentation Retention Contract

## Completed feature invariant

Each feature registered as delivered in `spec-kit/FEATURE_MAP.md` retains:

1. `specs/<feature>/spec.md` with accepted requirements and compatibility boundary;
2. `specs/<feature>/implementation-notes.md` with final evidence, residual risk and rollback information;
3. every normative contract file still referenced by product behavior, schemas, security policy or evidence.

## Transient classes

After convergence and durable-content review, the current tree need not retain `plan.md`, `research.md`, `data-model.md`,
`quickstart.md`, `tasks.md`, `analysis.md`, files below `checklists/`, or `spec-kit/feature-prompts/`. Their exact historical
content remains recoverable through Git.

## Classification

- Routine: PR description and proportionate tests; no feature directory.
- Standard: compact `spec.md` during implementation and `implementation-notes.md` before merge.
- High assurance: full Spec Kit lifecycle plus applicable ADR/evidence controls; compact only after convergence.

An unknown, mixed or disputed classification moves upward. Documentation classification never lowers executable CI,
security, coverage, compatibility or release requirements.
