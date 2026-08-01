# Implementation Plan: Repository Hygiene and Maintainability

**Branch**: `codex/f018-repository-hygiene` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

## Summary

Perform a behavior-preserving post-roadmap hygiene pass with three bounded code extractions: release-gate evaluation,
CLI command dispatch and watcher-scan reconciliation. Add a deterministic standard-library AST guard that records but
does not conceal existing oversized production modules/functions, rejects growth and forces obsolete exceptions to be
removed. Correct focused-test commands, stale governance references and implemented-status documentation. Preserve all
public/persisted contracts, frozen evidence, version axes and NO-GO decisions.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library `ast`, `dataclasses`, `json` and existing project dependencies; no new
runtime or development dependency

**Storage**: Existing filesystem CAS and SQLite revision 10 remain byte/behavior compatible; no migration

**Testing**: Existing black-box integration/security suites, new maintainability-policy unit/repository tests, focused
commands with `--no-cov`, full pytest with branch coverage and sockets disabled

**Target Platforms**: Linux, macOS and Windows with Python 3.12

**Performance Goals**: Audit all production Python modules in under two seconds; no measurable runtime-path performance
regression is introduced by helper extraction

**Constraints**: Pure refactoring, stable exception/output ordering, no dependency or public schema change, no generated
evidence drift, no virtual-environment deletion, exact deterministic diagnostics

**Scale/Scope**: 81 production modules, approximately 39,000 source lines, 1,400 functions and the three measured
hotspots `evaluate_release`, `_execute` and `reconcile_watch_scan`

**Contract/Version Impact**: Additive contributor policy only. Application `0.1.0rc1`, workspace revision 10, public
schema versions, Graph contract, interchange profile and release evidence remain unchanged.

## Constitution Check

### Before design

- **Articles I-II**: Frozen original/derived evidence bytes and persisted identities are explicit non-change boundaries.
- **Articles III-IV**: No new provider abstraction or representation is introduced; the audit uses the standard library.
- **Article V**: The audit parses repository source only and emits path/metric diagnostics; it executes no document data.
- **Article VI**: No identity, serialization, schema or durable write changes are permitted.
- **Article VII**: Context compilation and evidence selection behavior are outside the refactor.
- **Article VIII**: Characterization and policy-failure tests precede implementation; all mandatory gates remain intact.
- **Article IX**: Completion claims are limited to measured hotspots and deterministic repository evidence.
- **Article X**: Three bounded extractions replace a wholesale rewrite; no framework is added.
- **Article XI**: F018 has one branch/PR and the full lifecycle plus three-platform CI.
- **Article XII**: Public contracts and accepted ADR decisions remain authoritative and unchanged.

**Gate result**: PASS. No ADR is required because architecture, persistence and public contracts do not change.

## Project Structure

```text
quality/
└── maintainability-policy.json
scripts/
└── audit_maintainability.py
src/openardp/
├── adapters/sqlite_catalog.py
├── interfaces/cli.py
└── services/release_gate.py
tests/
├── unit/test_maintainability_audit.py
├── integration/test_release_gate.py
├── integration/test_watcher_catalog.py
└── test_repository_contract.py
specs/018-repository-hygiene/
├── contracts/maintainability-policy.md
├── checklists/{requirements,maintainability}.md
└── spec,plan,research,data-model,quickstart,tasks,analysis,implementation-notes.md
```

**Structure Decision**: Keep extracted helpers in their owning architectural modules so dependencies continue to point
inward. The standalone audit belongs under `scripts/`; its reviewed policy belongs under `quality/`. Splitting the
6,761-line catalog class across inheritance mixins is rejected because it would change internal ownership and typing
without independently improving behavior; F018 instead extracts the largest watcher transaction into cohesive methods
and prevents future structural growth.

## Phase 0: Research

[research.md](research.md) records baseline measurements, tooling choices, hotspot selection, alternatives and the
focused-coverage diagnosis. There are no unresolved clarifications.

## Phase 1: Design and contracts

- [data-model.md](data-model.md) defines maintainability-policy records and monotonic exception semantics.
- [contracts/maintainability-policy.md](contracts/maintainability-policy.md) defines the deterministic audit contract.
- [quickstart.md](quickstart.md) separates fast local validation from authoritative full gates.
- Existing CLI, release and watcher contracts are characterized by their current integration suites; no public contract
  is added or modified.

### Post-design constitution re-check

PASS. The design adds no runtime dependency, persistent state, network path, schema, identity algorithm, provider
behavior or release claim. Legacy debt remains explicit and can only stay equal or shrink.

## Implementation strategy

1. Freeze baseline metrics and add failing policy/characterization tests.
2. Implement the deterministic audit and integrate it into repository validation.
3. Decompose release-gate evaluation into validation, evidence checks, value checks and decision construction.
4. Decompose CLI dispatch into bounded pre-workspace, workspace-maintenance, ingestion/query and evidence handlers.
5. Decompose watcher reconciliation into incomplete-scan, identity/hint, per-entry, tombstone and publication helpers.
6. Correct all focused quickstarts, F017's stale constitution reference and current project-status/governance records.
7. Record before/after evidence, run convergence and publish only after all local/cross-platform gates pass.

## Complexity tracking

The policy's default ceilings are 1,000 lines per production module and 100 lines per function. Existing exceedances are
explicit path/qualified-name exceptions capped at their measured baseline; new exceedances and all growth fail. When an
exception falls at or below the default it becomes stale and fails until removed, making improvement monotonic.
