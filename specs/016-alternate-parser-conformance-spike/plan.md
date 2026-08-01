# Implementation Plan: Alternate Parser Conformance Spike

**Branch**: `codex/f016-alternate-parser-conformance-spike` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/016-alternate-parser-conformance-spike/spec.md`

## Summary

Add a deliberately isolated, standard-library-only conformance program that runs under
Python isolated/no-site mode and cannot import OpenARDP or third-party packages. It first
acts as an independent consumer of every F006 evidence fixture and golden identity vector,
then acts as a non-Docling producer for deterministic synthetic TXT/CSV inputs. A narrow
OpenARDP-side coordinator validates the alternate record set with the reference contracts,
binds exact input/executable/output digests and generates one fail-closed decision report.
The spike changes no runtime adapter, public evidence schema, workspace or application
version. Its result can support only a scoped thin-contract interoperability statement;
the contract remains experimental.

## Technical Context

**Language/Version**: Python 3.12 for both processes; the alternate process uses only the
standard library and runs with `-I -S`

**Primary Dependencies**: Python standard library; existing Pydantic v2 and RFC 8785
implementation only in the reference-side coordinator; no new dependency

**Storage**: committed synthetic TXT/CSV sources, deterministic canonical JSON records and
one generated decision report under `conformance/alternate-parser/v0.1.0/`; temporary
operation-owned output directories during tests

**Testing**: pytest with sockets disabled; subprocess isolation/import probes; corpus parity,
semantic-negative, path confinement, determinism, reference round-trip, report tamper and
generated-artifact drift tests; existing full repository gates and three-platform CI

**Target Platforms**: Linux, macOS and Windows with Python 3.12

**Project Type**: installable Python library plus repository conformance tooling

**Performance Goals**: focused conformance run completes within 10 seconds on each supported
CI platform; process output and each input file are bounded to 1 MiB; complete fixture tree
is bounded to 128 files and 8 MiB

**Constraints**: offline, deterministic, no current-working-directory dependency, no imports
from OpenARDP/Pydantic/RFC8785 in the alternate process, no floats or unsafe integers in
identity payloads, no source-body/path disclosure in results, no contract/schema change
without separate compatibility and ADR governance

**Scale/Scope**: existing 7 valid roots, 8 invalid roots, 1 coherent record set and 6
identity vectors; two alternate source fixtures; at least 1 native record, 3 references
and 1 projection per required source family

**Contract/Version Impact**: no public-contract change; evidence contract stays experimental
`0.1.0`; application version, workspace revision, provider profile versions and export
profiles remain unchanged. A new conformance-report profile `0.1.0` is repository evidence,
not a runtime public interchange contract.

**Trust/Operational Impact**: all fixture and parser content is untrusted data. Both scripts
accept only explicit bounded roots, reject traversal/symlinks, perform no network or durable
runtime mutation, and publish no output outside operation-owned paths. The alternate process
has bounded isolation, not a strong universal sandbox.

## Constitution Check

### Before design

- **Article I**: Original source fixtures are read-only; generated records retain exact
  source, native artifact, recipe and executable identities.
- **Article II**: Alternate native/projection output is deterministic derived data and can
  be discarded and regenerated.
- **Articles III-IV**: The design tests an independent implementation, preserves complete
  provider-native data, keeps neutral projections thin and explicitly avoids stabilization
  or semantic-equivalence claims.
- **Article V**: Source content remains data; the isolated process has explicit path, byte,
  output and network-free boundaries and is described as bounded isolation.
- **Article VI**: Persisted identities use RFC 8785/SHA-256 with explicit domains and reject
  unsupported JSON values; generated files are atomically replaced only by the coordinator.
- **Articles VIII-IX**: Tests precede implementation, every claim binds to deterministic raw
  observations and unfavorable results are first-class.
- **Articles X-XII**: This is one bounded feature without a runtime abstraction or migration;
  F015 is merged and green, and F016 keeps all version axes independent.

**Gate result**: PASS. No ADR-triggering change or exception is proposed.

## Project Structure

### Documentation (this feature)

```text
specs/016-alternate-parser-conformance-spike/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── conformance-profile.md
├── checklists/
│   ├── requirements.md
│   └── conformance.md
├── tasks.md
├── analysis.md
└── implementation-notes.md
```

### Source and evidence

```text
conformance/alternate-parser/v0.1.0/
├── manifest.json
├── sources/
│   ├── sample.txt
│   └── sample.csv
└── expected/
    ├── alternate-record-set.json
    └── decision.json
scripts/
├── alternate_evidence_process.py
└── validate_alternate_conformance.py
tests/
├── contract/test_alternate_conformance.py
└── security/test_alternate_conformance_boundaries.py
```

**Structure Decision**: Keep the independent implementation outside `src/` so it is
obviously not a runtime adapter and can run under `-I -S`. Keep reference orchestration in
`scripts/` because it is a maintainer conformance tool, not a product use case. Reuse the
existing F006 domain models only after subprocess output crosses the independence boundary.

## Phase 0: Research

Research resolves the isolation definition, canonical JSON subset, corpus coverage,
alternate parser scope, decision semantics and contract-governance boundary. Decisions are
recorded in [research.md](research.md); no `NEEDS CLARIFICATION` remains.

## Phase 1: Design and contracts

- [data-model.md](data-model.md) defines observations, alternate records and fail-closed
  decision invariants.
- [contracts/conformance-profile.md](contracts/conformance-profile.md) freezes the isolated
  process request/response and report profile.
- [quickstart.md](quickstart.md) provides the single offline reproduction path and expected
  outcomes.

### Post-design constitution re-check

PASS. The design adds no production adapter, cloud dependency, workspace mutation or public
contract change. It preserves the independent-process boundary, provider-native artifact,
thin projections, exact provenance and experimental status. Generated evidence is bounded,
reproducible and drift-checked on all supported platforms.

## Implementation strategy

1. Freeze manifest/profile and negative tests before implementing the isolated process.
2. Implement the independent consumer and prove it cannot import project dependencies.
3. Implement deterministic TXT/CSV production and reference-side validation.
4. Generate the decision from exact observations, document friction/non-claims, and add
   drift validation.
5. Run focused tests, complete repository gates, converge, then publish one F016 PR.

## Complexity tracking

No constitution violation or special complexity exception is required. The second process
duplicates only the minimum validation logic necessary to create genuine independence; it
is intentionally not abstracted into the reference runtime.
