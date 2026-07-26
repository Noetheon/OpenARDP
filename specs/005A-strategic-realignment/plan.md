# Implementation Plan: Strategic Realignment and Contract Boundary

**Branch**: `codex/f005a-strategic-realignment` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005A-strategic-realignment/spec.md`

## Summary

Curate the reviewed v3.1 blueprint into the live repository while preserving the implemented Features 001–005 and their runtime contracts. Existing unversioned governance filenames remain authoritative; v3.1 source files are retained only as labelled adoption inputs. The implementation updates claims, roadmap, constitution, decision records, feature prompts, operational guidance, contract examples, and offline repository validation without changing source code, public schemas, dependency metadata, or the lockfile.

## Technical Context

**Language/Version**: Markdown and JSON documentation; Python 3.12 for offline repository-contract validation

**Primary Dependencies**: Existing standard-library test utilities and the locked repository development toolchain; no new dependency

**Storage**: Version-controlled files only; no persisted runtime data change

**Testing**: Existing Ruff, format, strict mypy, pytest with network disabled and coverage gate; focused documentation/governance contract tests; link and whitespace validation

**Target Platform**: Linux, macOS, and Windows repository checkouts

**Project Type**: Local-first Python library/CLI with governed documentation and experimental interoperability contracts

**Performance Goals**: No runtime performance change; documentation validation remains deterministic and offline

**Constraints**: Preserve runtime behavior, public-schema semantics, dependency lock, persisted identifiers, accepted history, LF-normalized text, and zero-default-network posture

**Scale/Scope**: Curated v3.1 overlay, four new ADRs, 13 continuation prompts, constitution amendment, two design-guidance directories, current project documentation, and validation evidence

## Constitution Check

*GATE: Passed before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Pre-design evaluation |
|---|---|
| Originals and evidence preserved | PASS — Features 001–005, accepted ADRs, public schemas, and external blueprint source remain intact; changes use explicit amendment or supersession. |
| Derived data and indexes non-authoritative | PASS — the feature formalizes this existing invariant and adds no persisted derived data. |
| Local-first/provider-neutral core | PASS — no dependency, network, provider, or runtime change. |
| Untrusted document boundary | PASS — repository prompt material remains subordinate to `AGENTS.md` and cannot grant runtime authority. |
| Deterministic identity/atomicity | PASS — no identity algorithm or durable runtime write changes. |
| Progressive context | PASS — thin evidence projection and auditable receipts strengthen the principle without implementing later behavior. |
| Test-first quality | PASS — focused repository-contract tests precede documentation integration; all locked gates remain mandatory. |
| Measured claims | PASS — evidence classification and unsupported-claims policy are feature outcomes. |
| Simplicity/incremental delivery | PASS — F005A is documentation/governance only and remains isolated from F006+. |
| Specification/decision governance | PASS — the source hierarchy is made explicit; new architecture decisions receive ADRs before implementation. |

The planned constitution amendment is a governance-major `2.0.0` update because it changes product positioning and the provider-neutral representation boundary. It preserves or strengthens every existing safety and quality obligation.

### Post-design Re-check

PASS. Phase 1 introduces no runtime interface. The migration contract explicitly prevents changes to `src/`, `schemas/`, `pyproject.toml`, and `uv.lock`; the authority map prevents versioned source files from becoming parallel governance; and the quickstart validates both content and absence of runtime drift.

## Project Structure

### Documentation (this feature)

```text
specs/005A-strategic-realignment/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── governance-migration.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Repository Changes

```text
.specify/
├── feature.json
└── memory/constitution.md

README.md
START_HERE.md
CHANGELOG.md
AGENTS.md
VALIDATION.md

docs/
├── 00_EXECUTIVE_BRIEF.md ... 14_MIGRATION_FROM_PREVIOUS_BLUEPRINT.md
├── 00_REVISED_EXECUTIVE_BRIEF.md
├── 01_VISION_AND_POSITIONING.md ... 10_OPERATIONS_PRIVACY_SUPPLY_CHAIN.md
└── adr/
    ├── 0001-use-docling-as-default-parser.md
    ├── 0005-portable-zip-runtime-cas.md
    └── 0007-implementation-first.md ... 0010-contracts-before-adapters.md

spec-kit/
├── CONSTITUTION_SOURCE.md
├── CONSTITUTION_V3_SOURCE.md
├── FEATURE_MAP.md
├── FEATURE_MAP_V3.md
├── OPERATING_PROCEDURE.md
├── OPERATING_PROCEDURE_V3.md
└── feature-prompts/
    ├── 001-repository-baseline.md ... 005-lexical-search.md
    └── 005A-strategic-realignment.md ... 017-microsoft-graph-design-spike.md

contracts/
├── README.md
└── example-selection-receipt.json

conformance/
└── README.md

codex/
└── MASTER_SESSION_PROMPT.md

scripts/
└── validate_repository.py

specs/
└── README.md

tests/
└── test_repository_contract.py
```

**Structure Decision**: Preserve all established repository locations. Map candidate ADRs into `docs/adr/` and renumber them sequentially. Adopt v3.1 content into the existing authoritative constitution, feature map, and operating procedure while retaining version-suffixed files as clearly labelled migration sources. Remove obsolete future prompts only after the authoritative map and replacements exist; preserve merged feature specifications under `specs/`.

## Complexity Tracking

No constitution violations require justification.
