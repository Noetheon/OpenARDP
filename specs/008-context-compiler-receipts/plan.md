# Implementation Plan: Context Compiler and Selection Receipts

**Branch**: `codex/f008-context-bundles` | **Date**: 2026-07-26 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/008-context-compiler-receipts/spec.md`

## Summary

Add a provider-neutral deterministic context compiler that resolves an exact current
corpus snapshot, discovers verified lexical candidates from F005 text and F007 rich
evidence, applies freshness/trust/evidence rules, fits canonical context bytes under an
exact versioned estimator budget and persists one additive `ContextBundle 0.2.0` plus one
new body-free experimental `SelectionReceipt 0.1.0`. The bundle's discriminated
provenance cites either an existing F002 block or an F006 projection without fabricated
identifiers. A checksummed SQLite migration links both CAS objects atomically; CLI
commands compile context and inspect receipts. Replay reuses the recorded exact snapshot
and rejects algorithm, policy, tokenizer or integrity drift.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2, RFC 8785 helper, stdlib only for the compiler;
existing optional Docling extra remains an ingestion-time dependency and is never
imported by the context service

**Storage**: Existing filesystem SHA-256 CAS plus checksummed SQLite workspace migration
6; existing FTS5 accelerator for text and bounded verified scan for F007 projections

**Testing**: pytest with branch coverage and network disabled, Ruff, strict mypy native
and `win32`, deterministic schema/identity fixtures, migration/atomicity fault injection,
CLI snapshots and three-platform GitHub Actions

**Target Platform**: Linux, macOS and Windows on Python 3.12

**Project Type**: Local-first modular-monolith library and CLI

**Performance Goals**: Bounded by at most 32 exact scopes, 10,000 discovered records,
512 verified candidates and a 16 MiB canonical bundle; selection performs no network or
model call and reports measured timing without a universal latency claim

**Constraints**: Exact deterministic ordering and replay; no budget overflow; no body in
receipt/log/error; no trust promotion; verified indexes/objects only; atomic publication;
cancellation checkpoints; at least 85% branch coverage

**Scale/Scope**: Single local workspace/user; TXT/Markdown normalized blocks plus accepted
PDF/DOCX/PPTX F007 evidence; one deterministic lexical algorithm/profile version

**Contract/Version Impact**: Add public experimental `ContextBundle 0.2.0` and
`SelectionReceipt 0.1.0` schemas plus independent identity vectors; retain all nine
existing schema bytes including ContextBundle `0.1.0`. Add workspace revision 6 and
additive CLI/application surfaces. Application, workspace, bundle-contract and
receipt-contract versions advance independently; provider and export profiles do not
change.

**Trust/Operational Impact**: Task and document bodies are untrusted input. Context items
remain role `data`; the service performs no side effect, arbitrary path access, network
call or provider invocation. Receipts retain only digests/identifiers/reasons/accounting.
Cancellation and failures expose no compilation row; pre-commit immutable CAS objects
may remain recovery candidates. Older readers require a revision-5 backup.

## Constitution Check

| Article | Design result |
|---|---|
| I — Source truth | PASS — exact versions/native evidence remain authoritative and every item is source-pinned. |
| II — Disposable accelerators | PASS — FTS discovery is verified against catalog/CAS and drift fails closed. |
| III — Reuse/provider neutrality | PASS — stdlib/Pydantic core, no provider/model/network dependency, established JSON Schema/JCS reused. |
| IV — Thin projection | PASS — context selects F002/F006 evidence and never builds another rich-document model. |
| V — Data not instruction | PASS — task/evidence remain delimited data; no paths, URLs, imports or tools are executed. |
| VI — Determinism/atomicity | PASS — JCS/SHA-256 identities, total order, immutable CAS and one SQLite commit. |
| VII — Progressive context | PASS — task/budget/version-aware bundle plus complete selection receipt and explicit visual escalation. |
| VIII — Test-first quality | PASS — contract, identity, budget, security, persistence and CLI tests precede implementation where practical. |
| IX — Measured claims | PASS — only reproducible determinism/bound evidence claimed; timings retain environment caveats. |
| X — Simplicity | PASS — existing monolith/CAS/catalog/search reused; no model ranker, MCP, watcher, DAG or export. |
| XI — Feature isolation | PASS — F008 only, full lifecycle and three-platform gate; F009+ remain excluded. |
| XII — Contract evolution | PASS — additive experimental receipt `0.1.0`, independent workspace migration and unchanged earlier contracts. |

No constitution exception or ADR is required. The additive receipt implements an
already-governed experimental candidate and does not change an existing compatibility
guarantee. This check remains PASS after Phase 1 design.

## Project Structure

### Documentation

```text
specs/008-context-compiler-receipts/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── checklists/
│   ├── requirements.md
│   └── context-compiler.md
├── contracts/
│   ├── context-bundle-0.2.0.md
│   └── selection-receipt.md
└── tasks.md
```

### Source and tests

```text
src/openardp/
├── domain/
│   ├── context.py                  # unchanged ContextBundle 0.1.0 contract
│   └── context_compilation.py      # request, policy, candidate, receipt, result
├── ports/
│   ├── catalog.py                  # additive ContextCatalog persistence shapes
│   └── context.py                  # estimator and candidate-source protocols
├── adapters/
│   ├── context_estimators.py       # exact bytes/chars and conservative tokens
│   ├── context_candidates.py       # verified text/rich lexical discovery
│   ├── sqlite_migrations.py        # checksummed migration 6
│   └── sqlite_catalog.py           # atomic compilation commit/load/list
├── services/
│   └── context_compiler.py         # snapshot, selection, replay, verification
└── interfaces/
    └── cli.py                      # context and context-receipt commands

schemas/
├── context-bundle.schema.json       # byte-identical 0.1.0
├── context-bundle-0.2.0.schema.json
└── selection-receipt.schema.json

tests/
├── contract/test_context_ports.py
├── domain/test_context_compilation.py
├── fixtures/context/
├── integration/test_context_catalog.py
├── integration/test_context_compiler.py
├── integration/test_cli_context.py
├── security/test_context_boundaries.py
└── unit/
    ├── test_context_candidates.py
    └── test_context_estimators.py
```

**Structure Decision**: Extend the existing inward-pointing modular monolith. Pure
identity/invariants remain in `domain`; estimator/discovery and SQLite/CAS mechanics are
adapters; orchestration is one application service; CLI contains only parsing and
presentation. Two concrete candidate sources justify their narrow shared port.

## Implementation Phases

### Phase 0 — Baseline and contract freeze

- Freeze F007 `main`, current test count and all nine schema/vector/corpus hashes.
- Add failing ContextBundle `0.2.0` and SelectionReceipt model/schema/version/identity/
  fixture tests first.
- Prove all earlier public schema bytes remain unchanged.

### Phase 1 — Pure compilation domain and ports

- Define strict request, scope, limits, policy, algorithm, candidate, budget-ledger,
  decision, receipt and result records.
- Define exact receipt identity and deterministic bundle UUID derivation.
- Add estimator/candidate/catalog protocols without provider runtime types.

### Phase 2 — Verified discovery and accounting

- Implement versioned byte, character and conservative-token estimators.
- Resolve exact sorted corpus scopes.
- Discover F005 hits through coverage-checked FTS and reverify full text blocks.
- Scan accepted F007 projections within strict limits and reverify bodies.
- Normalize deterministic score keys and classify duplicate/stale/rejected candidates.

### Phase 3 — Selection, persistence and replay

- Apply mode/evidence/trust/freshness policy and total ordering.
- Build delimited untrusted `EvidenceItem` payloads and exact missing-evidence notices.
- Fit canonical bundle bytes under response/provenance/evidence accounting.
- Build body-free receipt, publish canonical objects, and atomically commit migration-6
  links and exact scope roots.
- Load/verify/replay by receipt identity with idempotent convergence.

### Phase 4 — Failure safety and CLI

- Add cancellation checkpoints and fault injection before/after each publication phase.
- Sanitize all failures and prove no task/body/path/traceback leakage.
- Add `context` and `context-receipt` JSON/human commands while preserving prior output.

### Phase 5 — Compatibility and convergence

- Run quickstart in fresh text/rich workspaces, repeat/replay and hostile fault matrix.
- Run all local gates, isolated core/rich wheels and byte-diff proof.
- Update public documentation, schema matrix, changelog, validation and rollback notes.
- Run final Spec Kit analysis and convergence before publication.

## Complexity Tracking

No constitution violation requires justification.
