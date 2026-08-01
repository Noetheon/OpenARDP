# Implementation Plan: Visual Evidence Escalation

**Branch**: `codex/f011-visual-evidence-escalation` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/011-visual-evidence-escalation/spec.md`

## Summary

Add an explicit local visual-materialization use case over accepted F006/F007 evidence:
resolve a target to exact page geometry, render/cache a bounded PDF page in a spawned
offline worker, create a deterministic PNG crop and publish a thin experimental visual
descriptor plus transactional workspace reachability. Existing F008 compilation gains a
verified handle-only visual candidate source while retaining honest missing-evidence
behavior. Optional OCR/caption providers remain unregistered by default and publish
bounded untrusted outputs through F010.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2 and RFC 8785 in core; optional exact
`pypdfium2==5.12.1` and `Pillow==12.3.0` visual extra; existing Docling extra remains
unchanged

**Storage**: Existing filesystem content-addressed store plus additive checksummed
SQLite workspace migration 8

**Testing**: pytest with branch coverage/network disabled, Ruff lint/format, strict
mypy, JSON Schema/fixture/vector drift validation, wheel/sdist build and three-platform
GitHub Actions

**Target Platform**: Linux, macOS and Windows local single-user environments

**Project Type**: Modular local Python library and CLI; no daemon, HTTP service or new
MCP mutation surface

**Performance Goals**: One canonical page render is reused by all exact crops on that
page; exact cache hits invoke the renderer zero times; all geometry uses bounded integer
arithmetic; context bundles carry handles rather than image bytes

**Constraints**: Offline by default; originals immutable; untrusted source/native/image
content; provider-neutral core; no complete second IR; process/resource limits; atomic
catalog visibility; deterministic persisted identities; explicit rights restrictions;
no implicit rendering or interpretation during compilation; rotation-adjusted parser/
renderer aspect mismatch above 1,000 PPM fails closed without stretching

**Scale/Scope**: Maximum 2,000 pages, 20,000 pixels per page dimension, 100 million page
pixels, 25 million crop pixels and 100 MiB per encoded object by default; one explicit
projection materialization per call; existing F008 corpus/candidate caps remain

**Contract/Version Impact**: Additive experimental
`VisualEvidenceDescriptor 0.1.0`, additive workspace revision 8 and one new accepted
ADR. Existing eleven public schemas/identities, F007 provider/native-export profiles,
ContextBundle 0.2.0, SelectionReceipt 0.1.0 and F009 MCP contract stay byte-compatible.
Application version remains `0.0.1`; export-profile versions are unaffected.

**Trust/Operational Impact**: PDF/image decoding adds optional native attack surface
inside a killable spawned offline worker. Source and model output remain untrusted data;
EXIF/native metadata cannot grant authority. CAS-first publication may leave complete
unreachable objects before an aborted catalog commit; F013 owns cleanup. Rights default
to local-only/export-denied. Logs/errors remain body/path-free.

## Constitution Check

*GATE: Passed before Phase 0 and rechecked after Phase 1.*

| Article | Result and evidence |
|---|---|
| I — Source truth | PASS — source bytes are never changed; every raster/crop binds exact source/native/projection identities and preserves original access. |
| II — Disposable derivations | PASS — page/crop/interpretation outputs are reproducible CAS artifacts with complete recipes; context uses verified authoritative records. |
| III — Reuse/provider neutrality | PASS — renderer, usage policy and interpreter are narrow ports; concrete libraries are optional and local; no egress/default model. |
| IV — Thin projection | PASS — one thin descriptor composes F006 anchors and retained native data; no complete page/layout IR or pointer equivalence claim. |
| V — Untrusted/bounded execution | PASS — document/image/model data has no instruction authority; spawned worker has network, time, dimension, byte and OS limits. |
| VI — Determinism/atomicity | PASS — versioned RFC 8785/SHA-256 identities, wheel-content-bound geometry/PNG recipes, CAS-first verification and one SQLite commit. |
| VII — Progressive context | PASS — explicit materialization, handle-only bundles, current-snapshot verification and preserved `visual_evidence_required`. |
| VIII — Test-first gates | PASS — contract/domain/security tests precede implementation; complete local and three-platform gates are mandatory. |
| IX — Measured claims | PASS — per-platform cross-process vectors, distinct native-wheel recipe identities and cache counts substantiate only bounded determinism/reuse claims; residual renderer risk is documented. |
| X — Simplicity | PASS — one bounded feature in the modular monolith; F012-F014 remain excluded. Separate ports are justified by provider independence and explicit optional-provider requirement. |
| XI — Isolation/cross-platform | PASS — dedicated branch/PR and full Spec Kit lifecycle; exact optional lock and Linux/macOS/Windows CI required. |
| XII — Governance | PASS — ADR 0012 precedes identity/schema implementation; compatibility axes and highest-level sources are explicit. |

Post-design recheck: PASS. Research chose composition over changing F006/F008, one
additive migration, and optional adapters rather than violating any article. No
constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/011-visual-evidence-escalation/
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── visual-evidence.md
├── contracts/
│   └── visual-evidence-contract.md
├── data-model.md
├── implementation-notes.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Source code and repository artifacts

```text
src/openardp/
├── adapters/
│   ├── context_candidates.py       # add verified visual candidates
│   ├── isolated_visual.py          # spawned bounded protocol
│   ├── sqlite_catalog.py           # migration-8 visual persistence
│   ├── sqlite_migrations.py
│   └── visual_pdfium.py            # optional renderer/PNG implementation
├── domain/
│   ├── context_compilation.py      # internal handle candidate shape
│   ├── identity.py                 # visual/raster identity functions
│   └── visual.py                   # visual contracts and invariants
├── interfaces/
│   └── cli.py                      # explicit materialize/inspect verbs
├── ports/
│   ├── catalog.py                  # VisualCatalog protocol
│   └── visual.py                   # renderer/policy/interpreter ports/errors
└── services/
    ├── context_compiler.py         # handle-only item construction
    ├── visual_evidence.py          # resolution/materialization/verification
    └── visual_interpretation.py    # explicit F010-backed interpretation

schemas/
└── visual-evidence-descriptor.schema.json

docs/
├── 03_DATA_MODEL_AND_PACKAGE.md
├── 05_CONTEXT_COMPILER_AND_MCP.md
├── 06_SECURITY_MODEL_V2.md
├── 08_ROADMAP_AND_GOVERNANCE.md
├── 09_CONTRACT_LIFECYCLE_AND_COMPATIBILITY.md
├── 10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md
└── adr/0012-visual-evidence-descriptors-and-rendering.md

tests/
├── contract/                       # schema, fixtures, identity, compatibility freeze
├── domain/                         # visual models/geometry/identity
├── integration/                    # workspace, service, context, CLI, reachability
├── security/                       # bombs, metadata, injection, failures, no-network
└── unit/                           # resolver, worker, adapter, candidates, interpretation
```

**Structure Decision**: Preserve the existing inward-dependency modular monolith.
Pure contracts/geometry live in `domain`, provider interfaces/errors in `ports`, native
PDF/image behavior in optional adapters, orchestration in services and only identifier-
scoped commands in CLI. SQLite/CAS remain the accepted storage adapters.

## Implementation Phases

### Phase 1 — Governance and contract tests

1. Accept ADR 0012 with visual descriptor, renderer and compatibility decisions.
2. Add failing domain/identity/schema fixtures and freeze tests first.
3. Implement pure domain records, transforms, identities, JSON Schema generation and
   exports without importing optional providers.

### Phase 2 — Optional isolated renderer

1. Declare exact optional visual dependencies and regenerate/review `uv.lock`.
2. Add strict renderer/interpreter/policy ports and stable failure taxonomy.
3. Implement pure native region resolution against accepted retained JSON.
4. Implement spawned streaming PDF render/crop protocol with network and resource
   controls, deterministic PNG profile and synthetic smoke/security tests.

### Phase 3 — Atomic persistence and service

1. Add checksummed migration 8 and `VisualCatalog` transactional operations.
2. Implement CAS-first materialization, page-raster reuse, descriptor verification,
   idempotence, cancellation/fault/concurrency handling and exact inspection.
3. Add reachability roots and upgrade/rollback integrity tests.

### Phase 4 — Context and optional interpretation

1. Add internal handle candidate invariants and verified canonical-profile visual
   discovery.
2. Emit handle-only ContextBundle items while preserving missing evidence, budgets,
   receipts and replay.
3. Implement provider-neutral OCR/caption result validation and explicit F010-backed
   publication with fake-provider tests; register no default provider.

### Phase 5 — Interfaces, docs and validation

1. Add identifier-scoped CLI materialize/inspect commands and stable JSON envelopes.
2. Update product/data/security/context/operations/compatibility/roadmap docs,
   changelog, schema inventory and implementation notes.
3. Run format/lint/type/tests/build/schema/repo/evidence gates, cross-platform PR CI,
   converge, merge and verify post-merge main CI.

## Validation Strategy

- Unit: integer geometry, anchor/native resolution, recipes/limits, identity, renderer
  protocol, stable error mapping, rights policy and optional interpretation.
- Contract: generated schema, valid/invalid fixtures, identity vectors and byte freeze of
  all prior public schemas/descriptors.
- Integration: synthetic PDF end-to-end materialization, page reuse, exact retry,
  revision upgrade, reachability, context before/after/head-change, CLI envelopes.
- Security: dimension/decompression/output bombs, malformed/encrypted PDF, metadata/
  prompt injection, egress attempt, timeout/crash/cancellation, CAS/catalog faults and
  concurrent requests.
- Cross-platform: optional dependency installation, spawned worker lifecycle,
  deterministic synthetic raster/crop vectors and complete repository gate.

## Rollback and recovery

- Code rollback: revert the F011 feature commit/merge.
- Workspace rollback: restore a pre-revision-8 backup; never delete or edit migration
  history manually.
- Optional dependency rollback: remove the `visual` extra; core and existing rich
  workflows continue, materialization reports dependency unavailable, and existing
  visual artifacts remain inspectable through provider-free contracts/CAS.
- CAS residue from an aborted pre-commit operation remains unreachable and is not a
  partial logical record. F013 will provide classified recovery/cleanup.

## Complexity Tracking

No constitution violations require justification.
