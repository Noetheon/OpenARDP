# Implementation Plan: Benchmark, Security and v0.1 Release Gate

**Branch**: `codex/f015-benchmark-security-release-gate` | **Date**: 2026-08-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/015-benchmark-security-release-gate/spec.md`

## Summary

Add a provider-neutral, offline release-evidence subsystem that records immutable raw
benchmark/security/reproduction observations, validates complete suite bundles, computes
deterministic statistics and applies one predeclared fail-closed v0.1 gate policy. A small
redistributable DOCX/PPTX/text corpus exercises all five required baselines, source edits,
retrieval judgments, budgets and hostile inputs. Existing runtime services are measured;
they are not altered to improve results. Maintainer commands generate/validate evidence,
normalize a CycloneDX 1.5 SBOM exported by the pinned `uv`, inspect built artifacts and emit
a closed machine decision plus generated Markdown report/claim map. The feature adds no
runtime dependency or workspace migration and accepts `NO-GO` as the correct result whenever
value, safety, supply-chain review or three-platform reproduction is incomplete.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library, existing Pydantic v2/RFC 8785 runtime,
locked optional Docling/visual profiles, and pinned `uv` 0.11.31 CycloneDX 1.5 export;
no new runtime dependency

**Storage**: immutable canonical JSON/JSONL evidence files in explicit local output
directories; existing SQLite revision 10 and filesystem CAS are read only except where
the benchmark creates operation-owned disposable workspaces

**Testing**: pytest with sockets disabled, property/boundary tests for statistics and gate
logic, synthetic benchmark/security suites, generated-schema/corpus/report drift checks,
artifact inspection, clean-install/upgrade/backup/restore smoke tests and three-platform CI

**Target Platforms**: Linux, macOS and Windows with Python 3.12; timing evidence is
environment-scoped and never compared across hosts

**Project Type**: installable Python library/CLI plus explicit maintainer evidence tools

**Performance Goals**: benchmark overhead outside the measured callable below 2% or 1 ms,
whichever is larger; raw observations streamed atomically; routine semantic/security release
suite under 5 minutes per CI platform; reference timing suite bounded to 30 minutes

**Constraints**: offline by default, no telemetry, no real documents, no hidden network,
no benchmark-specific runtime fast path, minimum seven independent timing repetitions,
deterministic 10,000-resample percentile bootstrap and strict finite-number/unit validation

**Scale/Scope**: three document/task families, five baselines, three context budgets,
bounded raw evidence up to 100,000 observations/64 MiB per suite and three platform bundles

**Contract/Version Impact**: new experimental release-evidence schema/protocol/gate-policy
family `0.1.0` and maintainer commands; installable application candidate becomes
`0.1.0rc1`, while final `0.1.0` remains prohibited until a later explicit publication
commit consumes a current `GO`; workspace revision 10 and all evidence/context/MCP/provider/
export profiles remain unchanged

**Trust/Operational Impact**: corpus and all provider output remain untrusted data;
maintainer commands accept explicit bounded paths and never run from MCP/watcher/document
content. Evidence/report writers are atomic, diagnostics are body/path/secret free, and
vulnerability snapshots are explicit time-scoped supporting input rather than hidden network
calls. A gate has no force/waive option.

## Constitution Check

### Before design

| Article | Gate | Result |
|---|---|---|
| I Source truth | benchmarks use immutable synthetic sources and never modify originals | PASS |
| II Disposable derivations | all benchmark workspaces/results are reproducible and identity-bound | PASS |
| III Reuse/provider neutrality | all strong baselines included; no mandatory provider/cloud | PASS |
| IV Thin projection | measures existing native/projection boundaries; adds no rich IR | PASS |
| V Data is not instruction | hostile data cannot authorize runners, paths, network or tools | PASS |
| VI Identity/atomicity | JCS/SHA-256 evidence identities and atomic no-overwrite publication | PASS |
| VII Progressive disclosure | body-free decision/report precedes optional raw observation inspection | PASS |
| VIII Test-first gates | schemas, statistics, negative fixtures and gate tests precede runner | PASS |
| IX Fair evidence | five baselines, raw samples, intervals, limits and negative results required | PASS |
| X Simplicity | existing dependencies/services plus maintainer subsystem; no daemon/database | PASS |
| XI Feature isolation | only F015 measurement/security/release decision; three-platform CI | PASS |
| XII Contract governance | independent experimental evidence version and generated schema | PASS |

### After design

- Raw observations bind protocol, corpus, configuration, canonical source-tree inventory,
  lockfile and
  environment profile. Timing values are evidence, never persisted content identity inputs.
- The gate policy is committed before benchmark results. It requires seven timing samples,
  complete five-baseline coverage, exact correctness/security invariants, three-platform
  semantic/install/recovery agreement and a current reviewed dependency snapshot.
- Distinct operational value is not a vague speed claim: warm OpenARDP retrieval/compiler
  must invoke the parser zero times, beat raw reparsing with non-overlapping 95% intervals,
  preserve all judged anchors, and compile the smallest declared budget with complete judged
  evidence coverage using at most 50% of direct persisted-native bytes.
- Persisted-native direct reuse and provider-native chunk/retrieval remain visible even when
  they outperform OpenARDP. No result is discarded because it is unfavorable.
- CycloneDX comes from locked `uv` export, then a deterministic validator strips volatile
  serial/timestamp fields, binds the lock hash, checks component/dependency completeness and
  enriches every component with the exact reviewed SPDX license expression or declared
  unresolved license name. Missing review facts block generation. Vulnerability disposition
  remains separate so no SBOM field is misrepresented as a security or legal conclusion.
- Shared CI is accepted for semantic/security/install/recovery reproduction, not universal
  latency claims. One declared reference environment owns the release timing threshold.
- No constitution exception or ADR is required: no storage algorithm, schema compatibility,
  authority boundary or mandatory dependency changes.

## Project Structure

### Feature documentation

```text
specs/015-benchmark-security-release-gate/
├── analysis.md
├── checklists/
│   ├── requirements.md
│   └── release-evidence.md
├── contracts/
│   ├── maintainer-commands.md
│   └── release-evidence.md
├── data-model.md
├── implementation-notes.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Source, evidence and tests

```text
src/openardp/
├── domain/release.py
├── ports/release.py
├── adapters/
│   ├── release_benchmarks.py
│   ├── release_evidence.py
│   ├── release_reproduction.py
│   ├── release_security.py
│   └── release_supply_chain.py
├── services/
│   ├── release_benchmarks.py
│   └── release_gate.py
└── interfaces/cli.py

schemas/
└── openardp-release-evidence.schema.json

benchmarks/release/v0.1.0/
├── corpus-manifest.json
├── gate-policy.json
├── judgments.json
├── dependency-review.json
├── sources/
└── hostile/

release/evidence/v0.1.0/
├── decision.json
├── report.md
├── claim-map.json
├── sbom.cdx.json
└── checksums.txt

scripts/
├── generate_release_corpus.py
├── generate_release_evidence.py
└── validate_release_evidence.py

tests/
├── contract/test_release_schema.py
├── domain/test_release.py
├── integration/test_release_benchmarks.py
├── integration/test_release_cli.py
├── integration/test_release_reproduction.py
├── security/test_release_boundaries.py
└── test_release_evidence_drift.py
```

**Structure Decision**: release identities and gate invariants are pure domain models;
filesystem/build/SBOM observation is an adapter, deterministic aggregation and decision are a
service, and CLI/scripts are trusted maintainer composition roots. Existing ingestion,
retrieval, compiler, recovery and interchange code is called through its current public
boundaries rather than copied.

## Phase 0 — Research and gate-policy closure

1. Freeze five baseline semantics, corpus/query/task parity and instrumentation rules.
2. Freeze observation identity, monotonic timing, valid-sample, bootstrap, rounding and
   environment-comparison rules before collecting results.
3. Freeze operational-value, correctness, security, privacy, supply-chain, install, upgrade,
   recovery and three-platform thresholds in policy `0.1.0`.
4. Select locked `uv` CycloneDX 1.5 export, deterministic license enrichment and separate
   reviewed OSV disposition; document preview-format residual risk and normalization.
5. Define honest `NO-GO` behavior for missing/stale/unavailable/unsupported evidence.

## Phase 1 — Contracts, corpus and deterministic decision core

1. Add closed models for protocol/config/environment, observations, judgments, suites,
   dependency findings, platform reproduction, policy, claim map and decision.
2. Generate the public release-evidence JSON Schema, canonical allowlisted source-tree
   inventory and invariant agreement tests.
3. Generate deterministic redistributable sources/edits/queries/judgments/hostile fixtures
   with manifest/license hashes and drift validation.
4. Implement finite numeric validation, median/MAD, deterministic percentile bootstrap,
   interval comparison, suite fingerprints and fail-closed policy evaluation.
5. Generate machine decision, Markdown report and claim map from one verified evidence graph;
   empirical correctness/budget ratios receive case-stratified bootstrap intervals in addition
   to exact full-corpus pass/fail checks.

## Phase 2 — Real runners and security/reproduction evidence

1. Implement all five baselines against actual Docling-native data and existing OpenARDP
   retrieval/compiler paths; instrument parser calls and storage without benchmark shortcuts.
2. Exercise cold/warm/edit runs, correctness judgments and three budgets; retain all raw
   observations and explicit unavailable/rejected records.
3. Aggregate existing hostile tests through a declared security manifest and add end-to-end
   injection, malformed-parser, drift, privacy-sentinel and failure-cleanup cases.
4. Build F014 `0.0.1` and F015 `0.1.0rc1` wheel/sdist artifacts from exact revisions, inspect
   inventories/hashes, enrich/validate CycloneDX, verify dependency disposition, perform fresh
   offline candidate install, previous-application reopen and revision-9 to 10 migration plus
   backup/restore drills in clean temporary environments.
5. Produce one platform evidence bundle per CI OS with pinned upload-artifact
   `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` (v7.0.1), then use pinned download-artifact
   `3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c` (v8.0.1) in one aggregate job that verifies
   all three identities and runs the same release gate.

## Phase 3 — Maintainer interface, reports and convergence

1. Add explicit `release-evidence`, `release-gate` and `release-report` commands with closed
   JSON, no implicit paths/network and no waiver option.
2. Commit the current candidate's machine/human decision. If evidence is incomplete or
   thresholds fail, commit truthful `NO-GO` with exact blockers; retain the candidate at
   `0.1.0rc1` and do not finalize `0.1.0`.
3. Update README claims, benchmark/security/operations/release/support docs and changelog to
   distinguish measured evidence, synthetic limitations and residual risk.
4. Run focused/full/schema/corpus/SBOM/build/install/repository gates, complete lifecycle
   artifacts and verify PR plus post-merge Linux/macOS/Windows CI before F016.

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
uv run python scripts/generate_release_corpus.py --check
uv run python scripts/generate_release_evidence.py --check
uv run python scripts/validate_release_evidence.py release/evidence/v0.1.0
uv run python scripts/validate_repository.py
```

The PR and post-merge `main` runs must pass Linux, macOS and Windows before F016 starts.
