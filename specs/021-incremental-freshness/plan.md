# Implementation Plan: Incremental Freshness Status

**Branch**: `codex/f021-incremental-freshness` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/021-incremental-freshness/spec.md`

## Summary

Split source freshness from complete stored-evidence verification without weakening either claim. The default path keeps
exact SHA-256 source inspection, reads one atomic document/head/representation-header snapshot and explicitly reports
`HEAD` integrity coverage; it never materializes block projections or reads block CAS. An opt-in service/CLI mode retains
the existing complete verifier and reports `FULL` only after success. A versioned offline benchmark reuses F020's frozen
10k/100k corpora, preserves its baselines and measures both operations separately.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Existing Python standard library, Pydantic v2, SQLite and RFC 8785 identity support; no new
dependency

**Storage**: Existing SQLite revision 10 and filesystem CAS; read-only F021 status evidence under
`benchmarks/freshness/v0.1.0/`; no migration

**Testing**: pytest with socket blocking and branch coverage; domain, port, SQLite, service, CLI, MCP, corruption,
concurrency, benchmark and drift tests

**Target Platform**: Linux, macOS and Windows semantics; macOS arm64 F020 host class for decision-bearing timings

**Project Type**: Python library/CLI/read-only MCP repository with maintainer benchmark tooling

**Performance Goals**: Default unchanged status p95 below 250 ms at both 10,000 and 100,000 prepared blocks after one
declared warm-up; zero block-projection materialization and zero block-object reads

**Constraints**: Exact source SHA-256 every request; no parser; no source/CAS mutation; full integrity still exhaustive;
no unbounded MCP mode; offline; body-free output; one warm-up and seven retained samples

**Scale/Scope**: One local document at 10k/100k blocks; unchanged, same-metadata changed, missing, concurrent-head and
native/manifest/projection/block corruption cases

**Contract/Version Impact**: Additive `SourceStatus.integrity_coverage` field and service/CLI full-mode selection;
unchanged freshness vocabulary, MCP input schema, application version, workspace revision, public evidence schemas,
provider profiles and export profile

**Trust/Operational Impact**: The fast path truthfully provides source plus catalog-head coverage, not arbitrary CAS
tamper detection. Full verification remains explicit and potentially expensive. MCP stays identifier-only, read-only and
bounded. Source content remains untrusted data and never initiates an action.

## Constitution Check

### Pre-research gate

- **Article I**: PASS — both modes are read-only and remain bound to exact source/head identities.
- **Article II**: PASS — accelerators remain non-authoritative; full verification remains available.
- **Article III**: PASS — no provider, cloud service or dependency is added.
- **Article IV**: PASS — no representation or provider-native contract changes.
- **Article V**: PASS — source content remains inert and MCP cannot request the expensive audit.
- **Article VI**: PASS — SHA-256, canonical identity and atomic catalog snapshots remain authoritative.
- **Article VII**: PASS — output is body-free, bounded and coverage-explicit.
- **Article VIII**: PASS — negative, corruption, concurrency and performance-counter tests precede implementation.
- **Article IX**: PASS — F020 baselines, raw samples and weaker fast-path coverage remain visible.
- **Article X**: PASS — one narrow snapshot method and one closed enum; no cache/framework abstraction.
- **Article XI**: PASS — isolated feature, complete lifecycle and three-platform gates.
- **Article XII**: PASS — ADR 0017 records the status semantic split; persisted/public identity contracts do not change.

### Post-design gate

PASS with no exception. The design changes no persisted identifier, schema, workspace revision, storage engine, provider
default or release decision. ADR 0017 makes the additive assurance semantics explicit.

## Project Structure

### Documentation (this feature)

```text
specs/021-incremental-freshness/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/status-contract.md
├── checklists/
├── analysis.md
├── implementation-notes.md
└── tasks.md
```

### Source Code (repository root)

```text
benchmarks/freshness/v0.1.0/
├── protocol.json
└── results/reference-macos-arm64/
    ├── observations.json
    ├── summary.json
    ├── decision.json
    ├── run-manifest.json
    └── report.md

docs/adr/0017-freshness-integrity-coverage.md

src/openardp/
├── domain/ingestion.py
├── ports/catalog.py
├── adapters/sqlite_document_queries.py
├── adapters/sqlite_catalog.py
├── services/document_query.py
├── interfaces/cli_query_arguments.py
├── interfaces/cli.py
└── interfaces/mcp_server.py

scripts/
├── freshness_benchmark.py
├── run_freshness_benchmark.py
└── validate_freshness_benchmark.py

tests/
├── domain/test_ingestion.py
├── integration/test_document_query.py
├── integration/test_cli.py
├── integration/test_mcp_server.py
├── integration/test_freshness_benchmark.py
└── test_freshness_benchmark_drift.py
```

**Structure Decision**: Keep the new coverage vocabulary in the domain, the atomic body-free snapshot in the existing
catalog port/SQLite adapter, orchestration in `DocumentQueryService`, and benchmark-only code under `scripts`. Focused
read-only SQLite projection and argparse grammar helpers keep the established F018 hotspot ceilings monotonic without
adding a runtime interface, cache or persistence layer.

## Implementation Phases

### Phase 0 — Freeze semantics and evidence

1. Accept ADR 0017 and freeze coverage vocabulary, request modes, target and F020 baselines.
2. Freeze a body-free benchmark protocol with exact counter and corruption requirements.

### Phase 1 — Domain and atomic catalog snapshot

1. Add closed integrity coverage and shape invariants.
2. Add one atomic document/head/representation-header snapshot method over existing rows.
3. Prove no migration or block projection materialization occurs.

### Phase 2 — Service and interfaces

1. Make exact default freshness use the header snapshot only.
2. Retain opt-in complete verification for service and CLI.
3. Add coverage projection to CLI/MCP while keeping MCP bounded.

### Phase 3 — Benchmark and evidence

1. Measure both paths at 10k/100k with F020 baselines and raw samples.
2. Validate tamper, privacy, deterministic report and target decision independently.
3. Commit actual results, full gates and convergence evidence.

## Complexity Tracking

No constitution violation or complexity exception is required.
