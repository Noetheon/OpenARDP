# Implementation Plan: Reconciliation and Derivation DAG

**Branch**: `codex/f010-reconciliation-derivation-dag`

**Specification**: [`spec.md`](spec.md)

**Baseline / rollback commit**: `1e2992c294cf67bc1f87ab58dbfa4b2555f264e6`
**Target**: Python 3.12, local SQLite/filesystem CAS, no new dependency

## Summary

Add one explicit, provider-neutral lifecycle layer above already-READY F002 block
aggregates. A pure bounded matcher produces conservative lineages and canonical
`same_logical_block_as` relations. A checksummed revision-7 catalog transaction stores
the complete reconciliation and changes derivation eligibility exactly. Separate
derivation services publish verified F002 generation records/outputs with typed direct
edges, cycle checks, slot supersession, transitive invalidation and A→B→A reactivation.

No ingestion path, head update, parser, rich-provider projection, MCP descriptor,
public JSON Schema, dependency or lockfile changes.

## Technical Context

- Existing content identity: RFC 8785/JCS through `openardp.domain.identity`.
- Existing evidence: F002 `ContentBlock`, `Relation`, `DerivationRecord`.
- Existing persistence: revision-6 `SQLiteCatalog`, filesystem CAS and restrictive
  object registry.
- Existing orchestration: synchronous ports/services with injectable clocks,
  cancellation callbacks and fault injectors.
- Concurrency: SQLite `BEGIN IMMEDIATE`, rollback journal, `synchronous=EXTRA`, busy
  timeout, unique constraints and idempotent compare-before-return.
- Test gate: offline pytest with branch coverage, Ruff, format, strict mypy, build,
  repository/schema/conformance drift checks and three-platform CI.

## Constitution Check

| Article | Required property | Plan evidence | Status |
|---|---|---|---|
| I Source truth | never rewrite sources/blocks | relations/lineages are additive; original and accepted block objects unchanged | PASS |
| II Derived data | reproducible and invalidatable | exact recipe/edges, state events, stale/reactivate closure | PASS |
| III Provider neutral | narrow existing ports, offline | F002 blocks only; no provider logic/dependency | PASS |
| IV Thin projection | no parallel rich IR | rich projections explicitly excluded | PASS |
| V Untrusted data | no content as instruction | matcher treats text as bounded data; body-free errors/logs | PASS |
| VI Identity/atomicity | SHA-256/JCS, atomic writes | ADR 0011 identities; CAS-first + one catalog transaction | PASS |
| VII Progressive delivery | preserve exact evidence | no interface bulk-return; verified handles/objects retained | PASS |
| VIII Tests | explicit invalidation/migration/security tests | domain, integration, failure, concurrency, corpus matrix | PASS |
| IX Measured claims | reproducible safety evidence | labelled corpus, precision/recall, zero-false-reuse gate | PASS |
| X Simplicity | modular monolith, bounded feature | two small services, one protocol extension, no framework | PASS |
| XI Isolation/quality | one branch/PR, all gates | F010-only file set and freeze checks | PASS |
| XII Governance | ADR before identifiers/migration | accepted ADR 0011; prior contracts frozen | PASS |

## Source Layout and Changes

```text
src/openardp/domain/
├── identity.py                 # additive identity helpers only
├── reconciliation.py           # pure matcher records, plan and bounded algorithm
└── derivation_lifecycle.py      # pure node/dependency/slot/event records

src/openardp/ports/catalog.py    # ReconciliationDerivationCatalog protocol + errors
src/openardp/adapters/
├── sqlite_migrations.py        # checksummed migration 7
└── sqlite_catalog.py           # atomic commits, closures, loads, reachability roots

src/openardp/services/
├── reconciliation.py           # verified aggregate loading, planning, CAS, commit
└── derivations.py              # canonical publication and verified lifecycle reads

tests/
├── fixtures/reconciliation/    # generated synthetic labelled edit corpus + vectors
├── domain/                     # models, matcher, identity, randomized DAG invariants
├── integration/                # catalog/service/migration/fault/concurrency/A→B→A
└── security/                   # body-free failure/logging and untrusted-text cases
```

Documentation changes are limited to ADR 0011, canonical incremental/data/architecture
guidance, README/changelog/validation and the complete F010 Spec Kit directory.

## Architecture and Data Flow

### Reconciliation

```text
explicit prior + target READY scopes
→ catalog loads complete aggregates
→ service verifies block CAS bytes/models/scope/hash
→ catalog supplies prior lineage memberships (or deterministic seeds)
→ pure bounded matcher produces complete plan
→ service canonicalizes/publishes relation objects to CAS and reverifies
→ one revision-7 transaction:
     insert/converge run
     seed prior lineages/members if absent
     insert target lineages/members and relation roots
     compute stale closure from inactive bindings
     compute deterministic reactivation fixed point
     append exact lifecycle events
  → commit complete result
```

The current document head is read and validated inside the write transaction before
lifecycle changes. The explicit target must be the current head for invalidation/
reactivation; historical-only reconciliation may persist lineages but cannot change
current derivation state. This avoids a stale caller invalidating a newer head.

### Derivation publication

```text
F002 record + typed dependencies + slot + optional output bytes/object
→ validate recipe, lifecycle shape and exact ordered inputs
→ publish/reverify canonical record and output in CAS
→ one revision-7 transaction:
     verify binding/object/producer dependencies
     reject self/ancestry cycle
     compare existing artifact for convergence/conflict
     create/converge slot
     supersede prior occupant if needed
     insert node + edges + lifecycle events
  → verify and return body-free node
```

The service API accepts bytes/chunks for output publication rather than filesystem
paths. It never invokes a model/provider and never accepts document text as commands.

## Matcher Design

1. Validate complete unique ordinals, hierarchy, document/scope and configured limits.
2. Derive bounded parent-context keys using persisted prior lineages and already
   accepted parent matches.
3. Execute fixed phases over unmatched indices. Candidate sets and iteration are
   sorted by stable reference tuples, never mapping insertion order.
4. Similarity uses deterministic normalized whitespace/casefold text only for logical
   continuity, limited to same kind/parent and sibling window. Fixed-point score and
   mutual-winner margin decide; text normalization never changes evidence identity.
5. Sequence phase operates only inside already bounded sibling gaps and only on exact
   signatures; ambiguous duplicates stay new.
6. Seed deterministic lineage identities for all unmatched current blocks.
7. Set `reusable` solely from exact canonical-hash equality.
8. Build valid F002 relations using the target representation's immutable `ready_at`
   for retry-stable provenance, then compute the result fingerprint.

## Transaction and Concurrency Design

- Extend the existing `_write_connection()` transaction; do not create another
  database layer.
- Parameterized SQL only. All new tables are STRICT with CHECK/FOREIGN KEY constraints.
- Unique target-scope and primary-key constraints arbitrate concurrent duplicates.
- On uniqueness conflict, reload inside the transaction and compare complete canonical
  facts: exact match converges, any mismatch raises a stable conflict.
- Fault injection occurs before every visibility boundary and before commit.
- Cancellation is cooperative and checked outside the transaction and immediately
  before commit; an exception rolls back the complete transaction.
- Recursive CTEs compute producer ancestry and invalidation candidates. Updates/events
  occur in deterministic sorted order.
- Revalidation runs to a bounded fixed point no larger than the number of stale nodes;
  exceeding that bound is treated as integrity/cycle failure.

## Integrity Verification

- `ReconciliationService` reuses strict public JSON loading and canonical byte checks
  for every block and relation object.
- `DerivationService` canonicalizes and verifies the F002 record object, verifies
  output object/hash and ensures edge digests equal the recipe tuple.
- Catalog load methods recompute lineage/binding/run/slot and row fingerprints.
- A lifecycle read verifies referenced record/output CAS objects through the service;
  catalog-only results remain body-free metadata.
- `reference_snapshot()` includes all historical relation/record/output roots.
- No corrupted row is silently repaired by a read or retry.

## Migration and Rollback

- Migration 7 is one append-only `Migration` value and becomes
  `CURRENT_SCHEMA_VERSION = 7`.
- Tests upgrade empty and revision-6 populated fixtures, compare every old table fact,
  inject each DDL failure and exercise concurrent initialization.
- Revision-7 software accepts and migrates 1–6 through the existing chain. Revision-6
  software rejects revision 7 as too new.
- Operational rollback: stop writers and restore the pre-upgrade workspace backup, or
  roll application code back only for workspaces that were never opened/upgraded.
  In-place downgrade is unsupported.

## Contract and Compatibility Plan

- No public schema generation change; all eleven JSON files must remain byte-identical.
- No existing golden identity vector changes; new F010 internal vectors live in the
  feature fixture corpus and do not redefine existing domains.
- No F006 conformance fixture or F009 descriptor change.
- Workspace migration and internal service/port models are additive application facts.
- ADR 0011 is the authoritative identity/migration decision.

## Test Strategy

### Test-first layers

1. Identity golden vectors and domain state/invariant tests.
2. Matcher phase tests plus generated labelled corpus and 20-process determinism.
3. Catalog migration/constraint/idempotency/conflict/cycle/closure tests.
4. Service CAS verification, failure/cancellation and concurrency tests.
5. Branching randomized DAG exact-closure tests with a pure reference oracle.
6. A→B→A end-to-end service test proving object identities are reused.
7. Reachability and body-free security/error/logging tests.
8. Repository/public-contract/dependency freeze tests.

### Corpus metrics

The fixture generator emits labelled cases and a manifest with expected relations and
reuse decisions. The audit reports:

- reusable true positives, false positives and false negatives;
- precision (must be exactly 1.000 when decisions exist);
- recall (reported, not allowed to weaken safety);
- ambiguity-to-new-lineage count;
- counts per matching phase.

Any false-positive reuse is an unconditional failure. Corpus expectations are reviewed
fixtures, not generated from the implementation under test.

## Observability and Privacy

- Log run/artifact/slot identifiers or digests, counts, stable outcomes and integer
  milliseconds only.
- Never log block text, similarity candidates, prompts, outputs, paths or provider data.
- Exceptions use fixed body-free messages; detailed constraint/SQLite text stays behind
  the internal debug boundary and is not surfaced by service APIs.

## Validation Commands

```bash
uv sync --frozen --all-extras --dev
uv run pre-commit validate-config
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/validate_repository.py
git diff --exit-code -- pyproject.toml uv.lock schemas conformance tests/fixtures/identity tests/fixtures/mcp
```

The PR must pass the equivalent locked Linux, macOS and Windows CI matrix. Post-merge
`main` CI is required before F011 begins.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| heuristic false match | ambiguity/new-lineage default; exact digest required for reuse; labelled zero-FP gate |
| quadratic input | fixed windows/comparison budget and fail-closed bounds |
| mutable state obscures immutable history | canonical record/output retained; append-only lifecycle events |
| graph cycle/corruption | existing-current producer requirement, recursive cycle check, bounded fixed point |
| stale caller changes newer head | transaction rechecks current head before lifecycle transition |
| partial cross-resource publish | CAS-first verification; single catalog transaction; idempotent retry |
| schema/contract creep | byte-freeze tests and no new public root |
| orphan growth after crashes | honest reachability reporting; F013 owns reclamation |

## Complexity Justification

New lineage and derivation lifecycle models are justified by two concrete consumers:
current F010 reconciliation/invalidation and planned F012 scheduling of the same narrow
ports. No generic graph framework is introduced; SQLite remains the only runtime store,
and algorithms are specific to accepted OpenARDP identities.
