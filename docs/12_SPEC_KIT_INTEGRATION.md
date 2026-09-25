# GitHub Spec Kit integration

## Decision

OpenARDP uses GitHub Spec Kit as an optional development-process toolkit for coding agents. Spec Kit does not define
the product or replace the architecture. Since Constitution 4.0.0, changes keep records in proportion to what they can
break: a scoped PR for documentation, tests and narrow fixes, a concise durable `spec.md` and `implementation-notes.md`
for behavior, contract and trust changes, and an ADR for irreversible decisions. Spec Kit stages are used when they
reduce a concrete risk; they are not gates.

## Why it is appropriate

OpenARDP is unusually sensitive to semantic drift. A superficially plausible implementation could accidentally:

- treat embeddings as authoritative or universal;
- overwrite original files;
- lose source/version provenance;
- permit document content to influence tools;
- rebuild parsers already provided by adapters;
- introduce mandatory cloud dependencies;
- claim performance improvements without benchmarks.

A constitution-driven workflow with lean durable records keeps these constraints visible without turning every change
into a large permanent dossier.

## Source-of-truth model

```text
Constitution and legal/security constraints
        ↓
Accepted ADRs and public schemas
        ↓
Project product requirements and architecture
        ↓
Durable feature records (spec.md, implementation-notes.md, contracts)
        ↓
Code and tests
```

A lower layer may implement or refine a higher layer but may not silently contradict it.

## Records by impact

| Change | Durable record |
|---|---|
| Docs, tests, internal refactoring or narrow fixes without behavior, contract or trust impact | PR evidence only |
| User-visible behavior, contracts, schemas, identity, migration, security/trust, providers or default dependencies | `spec.md` and `implementation-notes.md` |
| Irreversible or architectural decisions | Accepted ADR before implementation, plus the durable record |

No record choice weakens executable CI, security, coverage, compatibility or release gates.

## Optional Spec Kit lifecycle

When a change benefits from structured planning, the Spec Kit stages are:

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

## Retention and recovery

Completed features retain accepted `spec.md`, final `implementation-notes.md` and normative `contracts/`. Planning-time
`plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md`, `analysis.md`, checklists and generated prompts may
be removed after convergence, unique-content review and link migration. Their exact historical content remains available
through normal Git history. This reduces current-tree maintenance and navigation; it does not rewrite history or claim a
material reduction in historical clone size.

## Project-local template propagation

Feature 005A updates the checked-in Spec Kit templates because repeated omissions were observed around non-goals,
independent contract/version axes, trust/operational impact and mandatory tests. The constitution Sync Impact Report
records these dependencies. Future Spec Kit upgrades must preserve or intentionally migrate the project-local additions.

## Upgrade policy

1. Upgrade in a dedicated maintenance branch.
2. Commit or back up `.specify/memory/constitution.md` first.
3. Review release notes and generated-file diffs.
4. Reapply `scripts/apply-speckit-overlay.py`.
5. Run `specify integration status`.
6. Validate one disposable feature workflow before merging the upgrade.
