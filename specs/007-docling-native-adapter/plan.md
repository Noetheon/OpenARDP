# Implementation Plan: Docling Native Adapter

**Branch**: `codex/f007-docling-native-adapter` | **Date**: 2026-07-26 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`specs/007-docling-native-adapter/spec.md`

## Summary

Add an exactly locked optional Docling provider for local PDF/DOCX/PPTX. Extend the
existing source snapshot, representation lease, CAS and catalog lifecycle with additive
accepted-artifact, append-only parse-attempt and evidence rows. Parse only source bytes
in a spawned network-denied worker, retain complete canonical DoclingDocument JSON,
derive bounded F006 evidence, commit it atomically, and expose cache-safe CLI inspection
without changing any public evidence schema.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: existing Pydantic 2.12 and RFC 8785 façade; optional exact
`docling==2.114.0`; standard library multiprocessing, JSON and resource controls; no
remote provider

**Storage**: existing atomic filesystem CAS plus additive checksummed SQLite migration
`4 → 5` for rich artifact and evidence references

**Testing**: pytest with socket denial and branch coverage; pure model/property tests;
spawned-worker fault injection; catalog migration/atomicity tests; synthetic actual
DOCX/PPTX provider smoke tests; PDF local-assets negative gate; CLI integration; full
prior contract/conformance suite

**Target Platform**: Linux, macOS and Windows on Python 3.12; POSIX limits are
defense-in-depth and portable semantic/time/output limits apply everywhere

**Project Type**: local-first modular Python library and CLI

**Performance Goals**: unchanged exact input invokes the provider zero times after first
commit; worker termination within five seconds of timeout/cancellation handling; no
universal parse-throughput claim

**Constraints**: source maximum 100 MiB; 500 pages default; 120-second deadline; 4 GiB
POSIX address space; 64 descriptors; 256 MiB native JSON; 100,000 projections; 8 MiB per
retrieval body; 256 MiB aggregate retrieval; no network, source path, automatic model
download, OCR, remote service, executable deserialization or second rich IR

**Scale/Scope**: one provider, three media types, one native export profile, one evidence
profile, one additive migration, bounded CLI inspection and approximately 8–12 focused
source/test modules

**Contract/Version Impact**: F006 public roots remain byte-identical at experimental
`0.1.0`; workspace schema advances 4→5; Docling provider is 2.114.0; provider profile is
0.1.0; application remains 0.0.1 during feature development; export profiles unchanged

**Trust/Operational Impact**: untrusted archive/PDF/parser/native data; sockets denied
before provider import; local model paths validated but never persisted/logged; process
is bounded rather than strongly sandboxed; cancellation kills child; partial/disk-full
states fail closed; exact dependency/model license review required

## Constitution Check

*GATE: Passed before research and re-checked after design.*

| Gate | Evaluation |
|---|---|
| Source truth | PASS — original bytes remain immutable source CAS objects and every rich artifact binds to the exact version. |
| Disposable derived data | PASS — native/evidence/descriptor objects record recipe and may be rebuilt. |
| Implementation first/reuse | PASS — Docling is reused behind a port; the contract stays experimental. |
| Thin evidence projection | PASS — complete Docling JSON is retained; only F006 anchors/retrieval metadata are projected. |
| Data not instruction | PASS — source/provider data remains role data; no tools, URLs or pointer paths execute. |
| Bounded execution | PASS — spawned worker, no source path, offline mode, network denial and explicit limits; no sandbox overclaim. |
| Determinism/atomicity | PASS — SHA-256/JCS/CAS identities and one transactional READY commit. |
| Progressive disclosure | PASS — evidence listing is body-free; one body is fetched explicitly by projection ID. |
| Test-first quality | PASS — model, worker, persistence, security and CLI tests precede implementation where practical. |
| Measured claims | PASS — only reuse/termination evidence is claimed; provider nondeterminism is recorded. |
| Simplicity | PASS — existing lifecycle is extended; no alternate framework, context compiler, MCP or watcher. |
| Feature isolation | PASS — only F007 and migration 5; F008+ behavior excluded. |
| Contract evolution | PASS — no F006 change; provider/workspace versions evolve independently with migration evidence. |
| Supply chain | PASS — exact optional dependency, license/provenance/advisory review and all-platform lock/CI. |

No constitution exception or new ADR is required. ADRs 0001, 0008 and 0010 explicitly
authorize this provider/contract boundary; ADR 0002 authorizes SQLite/CAS for the MVP.

## Project Structure

### Documentation

```text
specs/007-docling-native-adapter/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── contracts/
│   └── docling-adapter.md
├── checklists/
│   ├── requirements.md
│   └── docling-adapter.md
└── tasks.md
```

### Source and tests

```text
src/openardp/
├── domain/
│   ├── ingestion.py
│   └── rich_ingestion.py
├── ports/
│   ├── catalog.py
│   └── parser.py
├── adapters/
│   ├── docling_native.py
│   ├── isolated_docling.py
│   ├── local_source.py
│   ├── sqlite_catalog.py
│   └── sqlite_migrations.py
├── services/
│   ├── rich_ingestion.py
│   └── rich_evidence.py
└── interfaces/
    └── cli.py

tests/
├── contract/
│   ├── test_ingestion_ports.py
│   └── test_docling_dependency.py
├── domain/
│   └── test_rich_ingestion.py
├── unit/
│   ├── test_docling_native.py
│   └── test_isolated_docling.py
├── integration/
│   ├── test_docling_smoke.py
│   ├── test_rich_catalog.py
│   ├── test_rich_ingestion.py
│   └── test_cli_rich.py
└── security/
    └── test_docling_boundaries.py

tests/fixtures/rich/
├── synthetic.docx
├── synthetic.pptx
└── synthetic.pdf
```

**Structure Decision**: Extend the current modular monolith. Pure bounded models remain
in `domain`; provider protocols stay in the existing parser/catalog ports; Docling and
process behavior live only in adapters; orchestration and verified retrieval live in
services; CLI remains the sole composition root. The binary fixtures are generated
deterministically by a reviewed script and contain no third-party or private content.

## Implementation phases

### Phase 0 — Baseline and dependency lock

- Freeze main commit and public artifact hashes.
- Add exact optional Docling dependency and lock graph.
- Prove core-only installation avoids provider import.
- Record package license/provenance/advisories and actual resolved graph.

### Phase 1 — Pure rich domain and port contracts

- Extend local media classification additively.
- Add strict limits, model manifest, descriptor, candidate/output/bundle and rich commit
  models.
- Extend parser/catalog ports without provider runtime types.
- Add failing identity, invariant, bound and compatibility tests first.

### Phase 2 — Docling native translation and worker

- Implement strict native export/projection/pointer logic over safe JSON, including the
  profile's exact decimal-string encoding of an out-of-range provider binary hash.
- Implement spawned worker, offline/network/resource controls and sanitized errors.
- Add actual synthetic DOCX/PPTX provider smoke tests and PDF-assets fail-closed test.

### Phase 3 — Atomic persistence and cache verification

- Add checksummed migration 5 with accepted-artifact links, append-only
  canonical/converged/diverged attempts and per-attempt evidence rows.
- Atomically commit canonical rich objects with existing representation/head/event;
  forced reparses append measured attempts without changing the accepted result.
- Verify complete cached aggregate before reuse.
- Cover migration, restart, conflict, tamper, disk failure and idempotency.

### Phase 4 — Service and CLI

- Orchestrate source snapshot, worker, CAS, F006 record construction and commit.
- Route rich media while preserving text behavior.
- Add body-free evidence listing and exact one-body retrieval.
- Cover force/reuse/change/cancellation and stable output/error envelopes.

### Phase 5 — Compatibility, documentation and convergence

- Preserve all nine schemas and both vector sets byte-for-byte.
- Run complete local and Windows-type gates, build and isolated installs.
- Update public docs/changelog/validation truthfully.
- Analyze, implement any findings, converge, publish one feature PR and verify main CI.

## Complexity Tracking

No constitution violations.

The additive catalog migration is justified by immediate durable facts from the single
Docling implementation and avoids a parallel lifecycle framework. The rich parser port
is justified by accepted ADR 0001/0008/0010 and deliberately shares the existing parser
module rather than creating an abstraction family.
