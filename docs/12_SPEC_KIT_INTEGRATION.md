# GitHub Spec Kit integration

## Decision

OpenARDP uses GitHub Spec Kit as the development-process layer for Codex. Spec Kit does not define the product or replace
the architecture. It turns the checked-in product, security and architecture decisions into bounded feature
specifications, plans, tasks, analysis gates and implementation/convergence loops.

## Why it is appropriate

OpenARDP is unusually sensitive to semantic drift. A superficially plausible implementation could accidentally:

- treat embeddings as authoritative or universal;
- overwrite original files;
- lose source/version provenance;
- permit document content to influence tools;
- rebuild parsers already provided by adapters;
- introduce mandatory cloud dependencies;
- claim performance improvements without benchmarks.

A constitution-driven, feature-bounded workflow keeps these constraints visible throughout implementation.

## Source-of-truth model

```text
Constitution and legal/security constraints
        ↓
Accepted ADRs and public schemas
        ↓
Project product requirements and architecture
        ↓
Active feature specification and plan
        ↓
Tasks
        ↓
Code and tests
```

A lower layer may implement or refine a higher layer but may not silently contradict it.

## Lifecycle

Every production-relevant feature follows:

1. **Constitution** — project rules already established.
2. **Specify** — what the bounded user/operator outcome is and why it matters.
3. **Clarify** — resolve material ambiguity before technical planning.
4. **Plan** — architecture, data model, contracts, security impact and tests.
5. **Checklist** — requirements-quality gate.
6. **Tasks** — dependency-ordered, path-specific implementation work.
7. **Analyze** — cross-artifact conflict and coverage check.
8. **Implement** — one bounded phase at a time.
9. **Converge** — compare the repository with all intended artifacts and append missing work.

## Integration mechanics

The repository pins a reviewed Spec Kit version in `spec-kit/PINNED_VERSION.txt`. The bootstrap script initializes the
Codex integration, then reapplies the authoritative OpenARDP constitution because Spec Kit initialization may replace its
managed memory/template files.

Generated Codex skills live in `.agents/skills/`. Feature artifacts live in `specs/`. Project architecture continues to
live in `docs/` rather than being copied into every feature folder.

## Deliberate non-use of custom templates in the first integration

The first integration keeps Spec Kit's core templates and enforces OpenARDP-specific requirements through the constitution,
feature prompts and `AGENTS.md`. This minimizes coupling to internal template placeholders and makes upgrades easier.
Project-local template overrides may be added later through a reviewed ADR if repeated omissions are observed.

## Upgrade policy

1. Upgrade in a dedicated maintenance branch.
2. Commit or back up `.specify/memory/constitution.md` first.
3. Review release notes and generated-file diffs.
4. Reapply `scripts/apply-speckit-overlay.py`.
5. Run `specify integration status`.
6. Validate one disposable feature workflow before merging the upgrade.
