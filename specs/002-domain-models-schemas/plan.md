# Implementation Plan: Domain Models and Interchange Schemas

**Branch**: `codex/f002-domain-models-schemas` | **Date**: 2026-07-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-domain-models-schemas/spec.md`

## Summary

Establish five strict, frozen Pydantic v2 record contracts for manifests, blocks, derivations, relations and context bundles; generate five reviewed JSON Schema 2020-12 documents from those models; and provide RFC 8785/JCS canonicalization plus explicit SHA-256 identity projections. Keep the domain layer pure and limit the change to contracts, deterministic identity helpers, fixtures, tests and contract documentation. Persistence, parsing, normalization workflows, retrieval, CLI and provider behavior remain outside F002.

## Technical Context

**Language/Version**: Python 3.12 (`>=3.12,<3.13`)

**Primary Dependencies**: Pydantic `>=2.12.5,<2.13` for validated models and schema generation; `rfc8785>=0.1.4,<0.2` behind an OpenARDP-owned canonicalization facade; no provider SDKs

**Storage**: N/A; no filesystem, database or artifact-store behavior in the installable domain package

**Testing**: pytest with branch coverage and network disabled; `jsonschema` Draft 2020-12 plus `FormatChecker`; RFC vectors; synthetic golden JSON; subprocess determinism checks

**Target Platform**: Linux, macOS and Windows on CPython 3.12 through the existing CI matrix

**Project Type**: Typed Python library with committed public JSON contracts

**Performance Goals**: No performance claim in this feature; determinism and bounded contract scope take precedence, and benchmarks remain Work Package 12

**Constraints**: Local/offline operation; pure domain code; no silent type coercion at public boundaries; no document-body logging; SHA-256 only; RFC 8785 canonicalization; exact supported schema release; synthetic/redistributable fixtures; no network in tests

**Scale/Scope**: Five root records, shared value objects, four domain-specific identity projections, five public schemas and a small golden corpus; no bulk ingestion or persistence scale is exercised

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

| Article | Gate | Plan response | Status |
|---|---|---|---|
| I — Evidence Preservation | Provenance and exact versions remain explicit; originals are not touched | Blocks and bundle items pin document, source version, representation and source location; F002 has no original-file I/O | PASS |
| II — Derived Data Is Disposable | Derivations record generator, version, inputs and time | Derivation contract separates recipe identity from output content hash and captures lifecycle metadata | PASS |
| III — Local-First and Provider-Neutral | No mandatory cloud/provider behavior | Only provider-neutral descriptors; no egress or service dependency | PASS |
| IV — Untrusted Document Boundary | Document content cannot become authority | Shared trust contract fixes `instruction_execution_allowed=false`; strict extras and JSON-only extensions | PASS |
| V — Determinism, Identity and Atomicity | SHA-256, canonical serialization and versioned algorithms | RFC 8785, domain-separated identity envelopes and explicit v1 projections; no durable writes in scope | PASS |
| VI — Progressive Context Delivery | Bundles remain version-pinned and auditable | Context contract includes exact scopes, evidence reasons, typed trace, warnings and missing evidence | PASS |
| VII — Test-First Quality Gates | Every contract/security/identity change tested offline | Tests precede implementation tasks; schema, semantic, RFC-vector, negative and subprocess coverage | PASS |
| VIII — Measured Claims | No unsupported performance/quality claims | No performance target invented; only reproducible correctness counts are claimed | PASS |
| IX — Simplicity and Incremental Delivery | Modular monolith and bounded feature | One domain package, no interfaces/ports without two implementations, no later work packages | PASS |
| X — Specification and Decision Governance | Higher-level conflicts corrected and changes traceable | Existing schema gaps are corrected as reviewed F002 contract changes; docs, ADR, schemas, fixtures and changelog move together | PASS |

**Post-design re-check**: PASS. The design introduces two small runtime dependencies and one shared base model because five concrete public records justify them. It introduces no service abstraction, persistence port, provider interface or architecture exception.

## Phase 0: Research Decisions

Research is consolidated in [research.md](research.md). All technical unknowns are resolved:

- RFC 8785/JCS is the canonical JSON contract; Python `json.dumps(sort_keys=True)` is explicitly not treated as cross-language canonical JSON.
- Pydantic is constrained to the reviewed 2.12 minor because generated schema text may drift across minors even without an intentional public-model change.
- Public JSON is checked for duplicate keys and invalid numeric values before Pydantic validation.
- The only installed schema release is `0.1.0`; unknown direct fields remain forbidden and forward-compatible experimental data belongs under `extensions`.
- Identity preimages are explicit and domain-separated; no complete model dump is hashed.
- Standard-schema constraints, record-semantic invariants and aggregate-semantic invariants are documented separately.

## Phase 1: Design and Contracts

- [data-model.md](data-model.md) defines field shapes, relationships and invariant ownership.
- [contracts/domain-contracts.md](contracts/domain-contracts.md) defines serialization, compatibility and identity projections.
- [quickstart.md](quickstart.md) defines runnable offline acceptance scenarios.
- [implementation-notes.md](implementation-notes.md) restates the work-package acceptance boundary and will record exact evidence.

## Project Structure

### Documentation (this feature)

```text
specs/002-domain-models-schemas/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── contracts/
│   └── domain-contracts.md
├── checklists/
│   ├── requirements.md
│   └── domain-contracts.md
└── tasks.md
```

### Source Code (repository root)

```text
src/openardp/domain/
├── __init__.py
├── common.py
├── identity.py
├── manifest.py
├── block.py
├── derivation.py
├── relation.py
└── context.py

schemas/
├── manifest.schema.json
├── block.schema.json
├── derivation.schema.json
├── relation.schema.json
├── context-bundle.schema.json
└── README.md

scripts/
└── generate_schemas.py

tests/
├── domain/
│   ├── test_common.py
│   ├── test_identity.py
│   └── test_models.py
├── contract/
│   └── test_domain_schemas.py
└── fixtures/domain/
    ├── manifest.json
    ├── block.json
    ├── derivation.json
    ├── relation.json
    ├── context-bundle.json
    └── canonicalization-vectors.json
```

**Structure Decision**: Keep each root contract in a small domain module and centralize only genuinely shared value types and identity primitives. Schema generation is repository tooling, not domain I/O. Tests separate pure model behavior from external JSON Schema contract checks.

## Complexity Tracking

No constitution violation or exception requires justification.
