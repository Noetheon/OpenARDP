# Implementation Plan: Reduce storage amplification without weakening evidence

**Branch**: `codex/f022-storage-amplification` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-storage-amplification/spec.md`

## Summary

Reduce the measured F020 logical workspace amplification from about 37.9x to at most 15x while retaining every source,
representation, block, historical version and evidence-verification guarantee. Workspace revision 11 normalizes repeated
representation scope metadata and folds disposable search projections into the block projection. Canonical F002-derived
block JSON may use a deterministic, dictionary-assisted per-object physical encoding whose logical SHA-256 identity and
exact replay bytes remain unchanged. Existing workspaces migrate and compact only through explicit, backup-first and
restart-safe maintenance operations. A frozen benchmark reports logical and allocated bytes, integrity, latency and
resource tradeoffs against the committed F020 baseline.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`hashlib`, `sqlite3`, `struct`, `tempfile`, `zlib`), Pydantic v2 and
the repository's existing runtime dependencies; no dependency or lockfile additions

**Storage**: SQLite catalog revision 11 plus filesystem content-addressed object store; atomic temporary-file publication
and SHA-256 logical identities remain authoritative

**Testing**: pytest with branch coverage, Hypothesis where existing property suites apply, Ruff and strict mypy; synthetic
and redistributable fixtures only; no network in tests

**Target Platform**: Python 3.12 on Linux, macOS and Windows; allocated-size binding threshold measured on macOS/APFS

**Project Type**: Local-first Python library and CLI

**Performance Goals**: Reference logical workspace `<=29,249,985` bytes, scale logical workspace `<=292,499,985` bytes,
at least 60% logical reduction from F020, and reference allocated workspace `<=107,249,945` bytes on APFS; report rather
than hide compression, migration, optimization, verification and retrieval costs

**Constraints**: Originals and native representations stay ordinary exact-byte leaves; exact logical bytes, identifiers,
history and compatibility guarantees cannot change; 16 MiB decoded compact-object ceiling; no automatic open-time
migration or compaction; no cloud/network requirement; malformed input fails closed

**Scale/Scope**: Frozen 10,000-line reference and 100,000-line scale edit/revert workloads, roughly 20,000 and 200,000
derived blocks respectively, plus revision-10 migration and interruption/retry scenarios

**Contract/Version Impact**: Internal workspace schema revision 10 to 11 and a new optional object-store capability plus
CLI maintenance surface. Public F002 schemas, object/block/representation identifiers, application version, provider
profiles and export profiles are unchanged. Older binaries require the verified revision-10 backup for rollback.

**Trust/Operational Impact**: Compact payloads are untrusted and decoded with a fixed dictionary, strict header/version,
logical-length bound, EOF/trailing-byte checks and post-decode digest verification. The catalog migration is backup-first;
physical optimization is explicit, idempotent and independently restartable. Backup, restore, reachability, diagnostics,
quarantine and integrity scans cover both physical layouts without double-counting logical objects. Logs and benchmark
artifacts remain body-free.

## Constitution Check

*GATE: Passed before research and re-checked after design.*

- **Article I — Source Truth and Evidence Preservation — PASS**: sources and provider-native artifacts remain exact,
  ordinary CAS objects; neither migration nor optimization rewrites them.
- **Article II — Derived Data and Disposable Accelerators — PASS**: only canonical derived F002 blocks are compacted;
  search metadata and contentless FTS remain rebuildable and canonical logical bytes remain reproducible.
- **Article III — Implementation First, Reuse and Provider Neutrality — PASS**: the physical encoding is an optional
  narrow provider capability and internal implementation detail; no standard claim, network or cloud dependency is added.
- **Article IV — Thin Evidence Projection — PASS**: catalog normalization retains only identity, navigation, trust and
  lifecycle fields; it creates no second complete document model and never replaces provider-native artifacts.
- **Article V — Data Is Not Instruction and Execution Is Bounded — PASS**: document content is never interpreted as
  commands; compact bytes, paths and catalog projections are untrusted, bounded and validated.
- **Article VI — Determinism, Identity and Atomicity — PASS**: SHA-256 logical identity is unchanged; the static dictionary,
  migration, publication and benchmark are deterministic, versioned and atomically persisted.
- **Article VII — Progressive Context Delivery — PASS**: block-level addressability and encoding-transparent evidence
  selection preserve the existing progressive, version-pinned context behavior.
- **Article VIII — Test-First Quality Gates — PASS**: codec, identity, schema, migration, source immutability and recovery
  changes have tests-first tasks plus all mandatory local gates.
- **Article IX — Fair Evidence and Measured Claims — PASS**: retained F020 baselines, frozen workloads, raw observations
  and unfavorable tradeoff reporting bind every storage claim.
- **Article X — Simplicity and Incremental Delivery — PASS**: F022 remains a local-monolith change and rejects packfiles,
  new native dependencies and unrelated architecture expansion.
- **Article XI — Feature Isolation and Cross-Platform Quality — PASS**: F022 is one bounded branch/PR with the complete
  Spec-Kit lifecycle, locked dependencies and Linux/macOS/Windows gates; F023 stays blocked until merge.
- **Article XII — Contract Evolution and Decision Governance — PASS**: ADR 0018 precedes persisted-layout work; workspace
  revision changes independently while public schema, application, provider and export versions stay fixed.

Post-design re-check against all twelve current articles: **PASS**. ADR 0018 is accepted before implementation; no constitutional exception or complexity
waiver is required.

## Project Structure

### Documentation (this feature)

```text
docs/adr/0018-compact-derived-block-storage.md
specs/022-storage-amplification/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── storage-optimization.md
├── checklists/
│   ├── requirements.md
│   └── storage-safety.md
└── tasks.md
```

### Source Code (repository root)

```text
src/openardp/
├── domain/
│   └── maintenance.py                  # body-free optimization result/invariant models
├── ports/
│   ├── object_store.py                 # optional compact/optimization capabilities
│   └── catalog.py                      # derived-block optimization inventory
├── adapters/
│   ├── compact_objects.py              # versioned bounded codec
│   ├── filesystem_cas.py               # dual-layout reads, writes and optimization
│   ├── filesystem_maintenance.py       # inventory/quarantine/backup physical awareness
│   ├── sqlite_catalog.py               # normalized scope/block/search queries
│   └── sqlite_migrations.py            # verified revision-11 migration
├── services/
│   ├── ingestion.py                    # optional compact block publication
│   └── storage_optimization.py         # explicit idempotent orchestration
└── interfaces/cli/
    └── main.py                          # storage-optimize command

scripts/
├── storage_benchmark.py                # frozen workload and measurements
├── run_storage_benchmark.py            # execution harness outside product package
└── validate_storage_benchmark.py       # body-free artifact and threshold validation

benchmarks/storage/v0.1.0/
├── README.md
├── baseline.json                       # pinned F020 comparison inputs
├── reference-result.json
└── scale-result.json

tests/
├── unit/
│   ├── adapters/test_compact_objects.py
│   ├── adapters/test_filesystem_cas.py
│   ├── adapters/test_sqlite_migrations.py
│   └── services/test_storage_optimization.py
├── integration/
│   ├── test_storage_revision_11.py
│   ├── test_storage_optimization_recovery.py
│   └── test_storage_backup_restore.py
└── contract/
    └── test_storage_benchmark_contract.py
```

**Structure Decision**: Preserve the existing inward-pointing domain/ports/adapters/services/interfaces architecture.
Codec mechanics stay in a small adapter helper; orchestration stays in a service; benchmark execution stays under
`scripts/` so maintainer-only machinery is not shipped as product code. Existing test paths may be extended instead of
creating a second file when that keeps a single contract coherent.

## Design and Delivery Sequence

1. Lock codec and schema behavior with failing unit and migration tests.
2. Add the bounded codec and optional filesystem capabilities without changing ordinary object-store behavior.
3. Add revision-11 schema migration, query rewrites and catalog invariants; validate exact pre/post logical behavior.
4. Route only fresh canonical F002 blocks through the compact capability with provider-neutral fallback.
5. Add explicit storage optimization, interruption recovery and dual-layout maintenance/backup/restore support.
6. Freeze and validate the body-free reference/scale benchmark and compare it against F020.
7. Run targeted tests, full local gates and trusted Linux/macOS/Windows CI; record unfavorable latency or allocation
   evidence rather than weakening the thresholds.

## Compatibility, Recovery and Rollback

- Revision-10 workspaces are never upgraded by ordinary open. The explicit migration first creates and verifies a full
  backup and records its digest before catalog mutation.
- Revision 11 retains all logical IDs, lengths, ordinals, navigation, trust metadata, search coverage and history. FTS
  rowids for already indexed blocks remain stable during migration.
- Physical optimization can be retried independently. Raw-only, compact-only and valid raw-plus-compact states all read
  the same logical object; valid duplicates are converged only by the explicit optimizer.
- Any malformed, unknown, oversized, truncated, trailing or digest-mismatched compact object fails closed. A corrupt
  duplicate is not silently hidden by a valid peer.
- Rollback means restoring the verified revision-10 backup with the existing restore workflow, not attempting an unsafe
  reverse SQL migration.

## Complexity Tracking

No constitution violations require justification. Multi-object packs, zstd/native dependencies, source compression and
moving canonical bodies into SQLite were explicitly rejected to keep this feature bounded.
