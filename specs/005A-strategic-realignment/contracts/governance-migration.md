# Governance Migration Contract

This contract defines the reviewable boundary for Feature 005A. It is a repository-governance contract, not an OpenARDP runtime or interchange contract.

## Inputs

- Clean repository state at commit `a23c07eb2a22efa7a4004d33cf00ab6cfd6fd027`
- Completed Features 001–005 and their accepted implementation evidence
- Reviewed OpenARDP Codex Blueprint v3.1 overlay
- Existing constitution 1.0.0, ADRs, public schemas, roadmap, prompts, and project documentation

## Required mappings

| Blueprint source | Repository destination | Treatment |
|---|---|---|
| `overlay/docs/*` | `docs/` | Curate as strategic/adoption guidance; reconcile active project docs |
| `overlay/spec-kit/*` | `spec-kit/` | Keep suffixed files as adoption sources; update canonical unsuffixed files |
| `overlay/adrs/*` | `docs/adr/0007-*` through `0010-*` | Renumber, reconcile, and accept through F005A |
| `overlay/contracts/*` | `contracts/` | Experimental design guidance only |
| `overlay/conformance/*` | `conformance/` | Future conformance guidance only |
| `overlay/codex/*` | `codex/` | Reproducible operator prompt, subordinate to repository governance |

## Preserved surfaces

The following paths MUST have no content diff in F005A:

- `src/`
- `schemas/`
- `pyproject.toml`
- `uv.lock`

Existing public command behavior, persisted identities, database behavior, and schema compatibility are outside scope.

## Authority order after migration

1. `.specify/memory/constitution.md` and accepted security/legal constraints
2. Accepted ADRs and public schemas
3. Canonical project documentation
4. Active feature specification and plan
5. Tasks
6. Implementation

Files explicitly labelled historical or adoption-source are evidence, not active authority.

## Acceptance protocol

1. Focused repository-contract tests fail before the governance integration.
2. The complete overlay is accounted for through the mapping table.
3. Obsolete future prompts are absent after replacement prompts exist.
4. No prohibited standards claim remains in active entry points.
5. Example JSON parses but is not registered as a public schema.
6. All repository gates pass offline and the package builds.
7. `git diff --check` and relative-link validation pass.
8. The preserved surfaces report no diff against the feature base commit.

## Rollback

Revert the single F005A merge commit or feature commit. No runtime data migration, dependency rollback, or workspace recovery step is required because the preserved surfaces do not change.
