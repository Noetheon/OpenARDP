# Implementation Notes: F010 Reconciliation and Derivation DAG

## Acceptance-criteria reconciliation

1. Reconcile only verified READY F002 block aggregates for the same document.
2. Match deterministically and conservatively; ambiguity creates a new lineage.
3. Persist canonical `same_logical_block_as` relations and complete membership
   atomically; logical similarity alone never permits derivative reuse.
4. Bind reuse to version-independent lineage plus exact canonical content digest.
5. Publish exact F002 derivation records/outputs with typed ordered direct dependencies,
   cycle checks, slots and internal `CURRENT/STALE/FAILED/SUPERSEDED` lifecycle.
6. Invalidate exactly the affected transitive closure, distinguish supersession, and
   reactivate immutable prior artifacts on exact A→B→A convergence.
7. Make CAS-first/catalog publication idempotent, restartable and cancellation/fault
   safe; complete unreachable residue is not partial logical publication.
8. Add only checksummed workspace revision 7; preserve public schemas, prior identities,
   conformance fixtures, dependencies and read-only MCP.
9. Prove zero false reuse on a reviewed labelled corpus plus migration, concurrency,
   reachability, privacy and three-platform quality evidence.

## Baseline and rollback

- Rollback commit: `1e2992c294cf67bc1f87ab58dbfa4b2555f264e6`
- Branch: `codex/f010-reconciliation-derivation-dag`
- Baseline package: Python 3.12.13, locked all-extras/dev environment.
- Initial worktree environment contained core-only dependencies; the first diagnostic
  run correctly produced 7 Docling/OOXML dependency failures and mypy import errors.
  `uv sync --frozen --all-extras --dev` installed only packages already in `uv.lock`;
  no repository file changed.

## Green pre-implementation baseline

| Command | Result |
|---|---|
| `uv sync --frozen --all-extras --dev` | success; existing lock only |
| `uv run pre-commit validate-config` | success |
| `uv run ruff check .` | success |
| `uv run ruff format --check .` | success; 111 files |
| `uv run mypy src` | success; 45 source files |
| `uv run pytest` | success; 843 passed, 87.10% coverage |
| `uv build` | success; wheel and sdist |
| `uv run python scripts/validate_repository.py` | success |

The baseline is remotely corroborated by post-F009 `main` CI run `30652185818` on
macOS, Ubuntu and Windows.

## Pre-implementation analysis

`analysis.md` records zero unresolved critical/high findings. The analysis corrected
retry-stable relation provenance, stale replacement semantics, current-head race
handling, F002/F010 lifecycle separation and active Spec Kit routing before runtime
implementation began.

## Implementation evidence

### Delivered boundary

- `domain/identity.py`, `domain/reconciliation.py` and
  `domain/derivation_lifecycle.py` provide four additive persisted identities, a pure
  bounded matcher, exact reuse bindings and strict lifecycle invariants without I/O.
- `ports/catalog.py`, `adapters/sqlite_migrations.py` and
  `adapters/sqlite_catalog.py` add the narrow catalog contract and append-only STRICT
  revision 7 with atomic reconciliation, derivation publication, invalidation,
  supersession and reactivation.
- `services/reconciliation.py` and `services/derivations.py` verify canonical F002/CAS
  inputs and publish CAS-first without invoking a parser, model or provider.
- ADR 0011, architecture/data/incremental/privacy guidance, quickstart and runtime
  contract describe the implemented boundary, backup/restore downgrade and exclusions.

### Measured evidence

| Evidence | Result |
|---|---|
| Focused domain/contract suite | 31 passed |
| Focused migration/catalog/oracle suite | 44 passed |
| Labelled reuse corpus | 130 decisions; 60 exact reusable; 0 false reuse; precision 1.000; recall 1.000 |
| Determinism | identity vectors in 20 fresh processes; full plans/relations in 10 fresh processes |
| Migration | populated revision 6→7 preservation; all 14 statement fault boundaries; concurrent installers; old-reader refusal |
| Lifecycle | all publication fault points; independent concurrent writers; cycle/dependency rejection; 100 reference-oracle DAGs; exact A→B→A reuse |
| Frozen contracts | eleven schemas, prior vectors, F006 corpus, F009 descriptors, `pyproject.toml` and `uv.lock` byte-identical to rollback |
| Full repository suite | 919 passed; 86.87% branch-aware coverage against 85% |
| Cross-platform static check | strict mypy passes for native and `--platform win32`, 49 source files |
| Distribution | wheel and sdist build; core wheel initializes revision 7 and imports F010 services in an isolated seven-package environment without Docling |

Fixture SHA-256 values are
`c0fc41cadf5a205465c44dbdbb88c40e9fc5c4ef4fd32a88213153709acb7bb1`
for the identity vectors and
`b24c97064da5fd9e813d42e7b8091255103b378a0962fbb857c10fa577f57cbe`
for the corpus manifest.

### Exact final commands

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run mypy src --platform win32
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/validate_repository.py
uv run python scripts/validate_evidence_contracts.py conformance/evidence/v0.1.0/manifest.json
uv run pre-commit run --all-files
git diff --check
```

The focused suites use `--no-cov` because repository configuration applies the global
85 percent threshold to every invocation; coverage authority is the complete suite.
An isolated virtual environment installed only the built core wheel and its six locked
runtime dependencies, initialized a fresh revision-7 catalog and imported both F010
services with `docling` absent.

### Tradeoffs and residual risks

- Ambiguity intentionally creates a new lineage, so recall may be lower on difficult
  edits; unsafe reuse remains categorically more expensive than regeneration.
- SQLite writer serialization and recursive closures are correct but not claimed to
  meet large-workspace performance targets before F015 benchmarks them.
- Rich F007 projections remain outside lineage reconciliation; immutable rich object
  hashes can still be exact derivation inputs.
- CAS-first interruption can leave complete unreachable objects. They are not visible
  as logical publications and F013 owns later retention/reclamation policy.
- F010 exposes explicit service APIs only. Scheduling, watchers, queues and MCP
  mutation remain later-feature work.

### Rollback

Originals and immutable CAS objects are never rewritten. Before upgrading a durable
workspace, copy both the SQLite database and CAS root while writers are stopped. There
is no in-place downgrade from revision 7: restore the paired pre-upgrade backup and run
the rollback commit. Older binaries fail closed on the newer schema.

### Remote convergence

- Feature commit `860ee5feb6292f2385195afe24f00c3bd3f02434` merged through
  [PR #14](https://github.com/Noetheon/OpenARDP/pull/14) as merge commit
  `52634115accc796d2655fe9a03dce50a9ac7f8de`.
- PR-head run
  [30658511214](https://github.com/Noetheon/OpenARDP/actions/runs/30658511214)
  passed the complete locked gate on Ubuntu, macOS and Windows before merge.
- Post-merge `main` run
  [30659080396](https://github.com/Noetheon/OpenARDP/actions/runs/30659080396)
  passed the same gate on macOS in 2m43s, Ubuntu in 4m21s and Windows in 8m52s.
- The first post-merge attempt was rejected before checkout by GitHub account billing;
  after the spending limit was corrected, the unchanged merge commit passed on all
  three platforms. This was infrastructure state, not a repository change.

F010 is converged with zero unresolved critical, high, medium or low implementation
finding. F011 may begin as a separate bounded Spec Kit feature.
