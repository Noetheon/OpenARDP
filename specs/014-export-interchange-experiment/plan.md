# Implementation Plan: Export and Interchange Experiment

**Branch**: `codex/f014-export-interchange-experiment` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/014-export-interchange-experiment/spec.md`

## Summary

Adopt RFC 8493 BagIt 1.0 as the existing integrity/package boundary and define a
narrow experimental OpenARDP BagIt profile `0.1.0`. The normative package is a
deterministic, uncompressed ZIP containing standard BagIt payload/tag manifests plus
one closed canonical OpenARDP metadata record. Export consumes an explicit portable
scope and affirmative asset policy; verification and import operate offline under
strict limits and publish only a fresh immutable package snapshot. No `.ardp` suffix,
workspace merge, remote retrieval, signature, new dependency or universal-format
claim is introduced.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library (`zipfile`, `hashlib`, `json`,
`tempfile`), Pydantic v2 and the locked RFC 8785 helper

**Storage**: deterministic ordinary ZIP files and fresh immutable imported snapshot
directories; existing SQLite/CAS workspace remains unchanged

**Testing**: pytest with network disabled, independent validator, deterministic golden
vectors, fault injection and concurrent process/thread tests

**Target Platforms**: Linux, macOS and Windows local filesystems

**Project Type**: installable Python library and explicit trusted-operator CLI

**Performance Goals**: constant-memory payload hashing/copying; reject at first limit
violation; deterministic output for identical semantic inputs

**Constraints**: offline; no source mutation; no archive extraction API; no links,
encryption, nested archives, compression, remote BagIt fetch, local paths or secrets;
fresh disjoint publication only

**Scale/Scope**: profile defaults cap the archive at 2 GiB, 10,000 entries, 1 GiB per
entry, 2 GiB expanded bytes, 16 MiB normative metadata, 512 UTF-8 path bytes, 16 path
segments and 100,000 declared relationships; tests exercise smaller override limits

**Contract/Version Impact**: new experimental export profile `0.1.0` and public
interchange JSON Schema `0.1.0`; application remains `0.0.1`, workspace/catalog remains
revision 10, and all existing public/provider/MCP contracts remain unchanged

**Trust/Operational Impact**: archives and all contained records remain untrusted;
integrity proves byte equality only. Export/verify/import are explicit CLI actions;
no MCP, watcher, startup, provider or document content can initiate them. Imports
stage beside an absent target, verify completely, synchronize and atomically rename.

## Constitution Check

### Before design

| Article | Gate | Result |
|---|---|---|
| I Source truth | source inputs are read/verified and never modified | PASS |
| II Disposable derivations | records preserve derivation status without promoting derived bytes | PASS |
| III Reuse/provider neutrality | reuse BagIt and stdlib ZIP; no provider dependency | PASS |
| IV Thin projection | one portable evidence projection, not a second parser IR | PASS |
| V Data is not instruction | no content execution, fetching, plugins or trust elevation | PASS |
| VI Identity/atomicity | JCS/SHA-256 inventory and fresh atomic publication | PASS |
| VII Progressive disclosure | bounded body-free reports precede snapshot inspection | PASS |
| VIII Test-first gates | vector and failure tests precede adapters/CLI | PASS |
| IX Measured claims | deterministic/cross-platform claims require committed evidence | PASS |
| X Simplicity | no dependency, database revision, daemon or custom suffix | PASS |
| XI Feature isolation | only F014 decision/profile/export/verify/import experiment | PASS |
| XII Contract governance | ADR, independent version, schema and compatibility guidance | PASS |

### After design

- RFC 8493 BagIt remains the package/inventory standard. OpenARDP adds one explicitly
  named profile tag and semantic record; it does not redefine the container.
- ZIP is only deterministic transport for the bag directory. The reader accepts the
  exact stored-entry profile and never calls `extract`, follows links or fetches URLs.
- The profile disallows `fetch.txt`; SHA-256 payload and tag manifests are exhaustive.
- Import publication is a fresh snapshot, not a workspace/catalog merge. This avoids a
  second cross-resource transaction protocol and keeps F013 recovery authoritative.
- RO-Crate remains a possible future additive semantic mapping. OCFL is rejected for
  one-shot exchange because its durable repository/version layout exceeds the need.
- All gates remain PASS. No Complexity Tracking exception is required.

## Project Structure

### Feature documentation

```text
specs/014-export-interchange-experiment/
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── interchange-security.md
├── contracts/
│   ├── bagit-profile.md
│   └── operator-cli.md
├── data-model.md
├── implementation-notes.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Source and tests

```text
src/openardp/
├── adapters/
│   └── bagit_interchange.py
├── domain/
│   └── interchange.py
├── ports/
│   └── interchange.py
├── services/
│   └── interchange.py
└── interfaces/
    └── cli.py

schemas/
└── openardp-interchange-package.schema.json

conformance/interchange/v0.1.0/
├── manifest.json
├── valid/
└── invalid/

scripts/
├── generate_interchange_vectors.py
└── validate_interchange_package.py

tests/
├── contract/test_interchange_port.py
├── domain/test_interchange.py
├── integration/test_bagit_interchange.py
├── integration/test_interchange_cli.py
├── security/test_interchange_boundaries.py
└── test_interchange_conformance.py
```

## Phase 0 — Research and decision closure

1. Compare RO-Crate 1.2, OCFL 1.1, BagIt 1.0 and a minimal project archive against
   one matrix of integrity, completeness, semantics, extensions, streaming, security,
   interoperability and dependency cost.
2. Accept BagIt 1.0 plus a narrow OpenARDP profile; reject a custom format, remote
   `fetch.txt`, OCFL repository semantics and normative JSON-LD for this experiment.
3. Freeze deterministic ZIP normalization, portable path grammar, resource ceilings,
   asset disposition, extension policy and trust semantics.
4. Record the decision and residual limits in ADR 0015.

## Phase 1 — Domain, profile and independent validator

1. Add closed Pydantic models for the profile record, exact assets, dispositions,
   inventory, export request, limits and body-free results.
2. Generate a strict JSON Schema and add an invariant/schema agreement matrix.
3. Implement a runtime-independent parser/validator over bytes/path-like input that
   validates ZIP metadata, BagIt structure, canonical JSON, manifests, digests,
   relationships, versions and limits without extraction.
4. Commit deterministic valid/invalid synthetic vectors and a drift-check generator.

## Phase 2 — Export and verified snapshot import

1. Implement an export service over a narrow source-byte reader port. Materialize
   policy-approved assets under canonical content-ID paths, produce canonical record
   bytes and exhaustive manifests, then self-verify before no-overwrite publication.
2. Implement import preflight as the independent validator plus an immutable import
   plan. Copy only allowlisted members to operation-owned sibling staging through safe
   file descriptors, rehash every file, synchronize and atomically rename.
3. Make repeated exact imports converge only after full re-verification; reject foreign
   or conflicting destinations and clean only operation-owned staging.

## Phase 3 — CLI, documentation and convergence

1. Add explicit `package-export`, `package-verify` and `package-import` commands using
   bounded JSON input/output and sanitized stable error categories.
2. Publish ADR, profile contract, compatibility, threat-model, data-model, README,
   conformance and changelog updates with precise non-claims.
3. Run focused/full/package/schema/repository gates, complete all checklist/tasks and
   verify Linux/macOS/Windows PR plus post-merge `main` CI before F015.

## Complexity Tracking

No constitution violations require an exception.

## Quality Gate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
uv build
uv run python scripts/generate_schemas.py --check
uv run python scripts/generate_interchange_vectors.py --check
uv run python scripts/validate_interchange_package.py \
  conformance/interchange/v0.1.0/valid/minimal.zip
uv run python scripts/validate_repository.py
```

The final PR and post-merge `main` run must pass Linux, macOS and Windows before F015
begins.
