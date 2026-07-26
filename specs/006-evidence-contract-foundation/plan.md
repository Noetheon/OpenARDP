# Implementation Plan: Evidence Contract Foundation

**Branch**: `codex/f006-evidence-contract-foundation` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-evidence-contract-foundation/spec.md`

## Summary

Add four closed, experimental provider-neutral contract roots before the Docling adapter:
native representation, evidence reference, thin evidence projection, and trust
classification. Reuse the existing strict Pydantic/JCS boundary, extend deterministic
JSON Schema generation additively, publish synthetic conformance fixtures and a
path-confined standalone validator, and preserve every existing Feature 005 schema and
identity vector unchanged.

## Technical Context

**Language/Version**: Python 3.12 and JSON Schema Draft 2020-12

**Primary Dependencies**: Existing Pydantic 2.12 and `rfc8785` façade; standard library;
no new runtime or development dependency

**Storage**: Version-controlled schemas and synthetic fixtures only; no catalog migration
or runtime persistence change

**Testing**: pytest with socket denial and branch coverage; jsonschema parity; strict
raw-JSON tests; deterministic schema/identity fixture checks; standalone conformance
validator; full repository gates

**Target Platform**: Linux, macOS, and Windows with byte-identical generated contracts

**Project Type**: Local-first Python library/CLI with provider-neutral JSON contracts

**Performance Goals**: Deterministic bounded validation of the reviewed fixture corpus;
no runtime ingestion or retrieval performance claim

**Constraints**: Offline, closed direct fields, JCS/I-JSON subset, SHA-256 identities,
fixed-point geometry, no adapter import, no pointer dereference, no complete neutral IR,
no existing-schema drift

**Scale/Scope**: Four root models/schemas; four anchor variants; focused domain,
contract, security, and repository tests; a bounded conformance corpus and validator

**Contract/Version Impact**: Add experimental evidence contract family `0.1.0`.
Application version remains `0.0.1`; workspace schema, provider-profile versions, and
export-profile versions are unchanged. Existing public schema release `0.1.0` remains
byte-for-byte compatible.

**Trust/Operational Impact**: Adds explicit source/effective trust enforcement and
data-only non-execution. Raw JSON, pointers, extension values, and fixture contents remain
untrusted data. Validation performs no network activity, parser execution, pointer
resolution, catalog mutation, or source-file access beyond caller-supplied fixture paths.

## Constitution Check

*GATE: Passed before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Pre-design evaluation |
|---|---|
| Source truth and provenance | PASS — every record is bound to exact source and native artifact identities; no original is modified. |
| Derived artifacts disposable | PASS — native/projection records carry generator, input, artifact, version, and time facts. |
| Reuse/provider neutrality | PASS — RFC 8785, JSON Schema, PROV, and Web Annotation are reused where suitable; no provider is mandatory. |
| Thin evidence projection | PASS — the projection contains references, navigation, retrieval handles, trust, and lifecycle only. |
| Data is not instruction | PASS — role is data, execution is false, pointers are opaque, and validation has no side effects. |
| Determinism and identity | PASS — purpose-specific versioned JCS envelopes and SHA-256 are explicit. |
| Test-first quality | PASS — fixture, contract, identity, version, and security tests precede model implementation where practical. |
| Simplicity/incremental delivery | PASS — four roots are the smallest accepted boundary needed by F007; no adapter or storage abstraction is added. |
| Feature isolation | PASS — one F006 branch/PR based on merged F005A; F007 work is excluded. |
| Contract evolution | PASS — additive experimental family, independent version, fixtures, migration note, and no prior-schema change. |

### Post-design Re-check

PASS. The data model keeps anchor/provider details bounded, uses fixed-point page
geometry to avoid cross-language float edge cases, represents retrieval as immutable
content-addressed handles rather than a duplicated tree, and confines cross-record
validation to a pure domain function. The standards guide is optional mapping guidance,
not a wire dependency. No constitution exception or complexity waiver is required.

## Project Structure

### Documentation (this feature)

```text
specs/006-evidence-contract-foundation/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── evidence-contracts.md
├── checklists/
│   ├── requirements.md
│   └── evidence-contracts.md
├── implementation-notes.md
└── tasks.md
```

### Source Code (repository root)

```text
src/openardp/domain/
├── evidence.py
└── identity.py

schemas/
├── native-representation.schema.json
├── evidence-reference.schema.json
├── evidence-projection.schema.json
└── trust-classification.schema.json

conformance/evidence/v0.1.0/
├── manifest.json
├── canonicalization-vectors.json
├── valid/
└── invalid/

scripts/
├── generate_schemas.py
└── validate_evidence_contracts.py

tests/
├── contract/test_evidence_schemas.py
├── domain/test_evidence_contracts.py
└── security/test_evidence_boundaries.py
```

**Structure Decision**: Extend the existing modular-monolith domain and deterministic
schema tooling. Pure record and cross-record invariants remain in `domain/`; the
standalone script composes those APIs but imports no adapter, service, catalog, or
interface code. Reviewed public fixtures live under `conformance/`; tests may add helper
fixtures under `tests/fixtures/evidence/` only when they are not public vectors.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
