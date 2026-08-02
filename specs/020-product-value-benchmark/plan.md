# Implementation Plan: Product Value Benchmark

**Branch**: `codex/f020-product-value-benchmark` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/020-product-value-benchmark/spec.md`

## Summary

Add a versioned, offline and fail-closed product-value benchmark that exercises the delivered ingestion, verified
retrieval, context compilation, deterministic replay, freshness and rich-document reuse paths against raw-reparse and
persisted-native baselines. It generates bounded synthetic 10,000- and 100,000-block corpora, retains raw timing and
correctness observations, computes uncertainty and amortization, and emits an immutable three-state worth-it decision
plus human report. The feature evaluates the product; it does not tune production behavior or alter the existing F015
release decision.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Python standard library, existing Pydantic v2 and RFC 8785 identity support; delivered optional
`docling==2.114.0` only for real rich-format treatments; no new dependency

**Storage**: Temporary generated corpus, existing local filesystem CAS and SQLite workspace, immutable JSON benchmark
evidence and Markdown projection

**Testing**: pytest with socket blocking and branch coverage; focused unit/integration/drift tests; Ruff, format, strict
mypy, build and repository validation

**Target Platform**: Decision-bearing reference timing on the current macOS arm64 host; semantic execution on Linux,
macOS and Windows CI; local offline operation only

**Project Type**: Python library/CLI repository with maintainer benchmark tooling

**Performance Goals**: Measure the existing PRD targets of unchanged status p95 under 250 ms and exact lexical search
p95 under 300 ms at 100,000 blocks; do not modify production behavior to force either result

**Constraints**: No network, no source mutation, no proprietary fixtures, at least seven retained repetitions, 100 MB
source and 100,000-block product limits, bounded result size, body-free evidence, no silent treatment substitution

**Scale/Scope**: Smoke profile for automated tests; 10,000-block reference profile; 100,000-block scale profile; fixed
DOCX/PPTX/PDF rich fixtures; exact lookup, context, replay, unchanged and edited-source workloads

**Contract/Version Impact**: No application, workspace, evidence-contract, provider-profile or export-profile change.
Benchmark evidence has an internal experimental `0.1.0` format and is not added to public schemas.

**Trust/Operational Impact**: Generated document content remains untrusted data. Benchmark workers inherit the delivered
offline parser boundaries. Output uses stable identifiers and sanitized environment classes, publishes atomically,
records unavailability instead of raw exceptions, and never grants a document side-effect authority.

## Constitution Check

### Pre-research gate

- **Article I**: PASS — original committed fixtures are read-only; edits occur only on generated copies.
- **Article II**: PASS — corpus, workspaces and aggregates are derived, identifiable and reproducible.
- **Article III**: PASS — the harness evaluates existing implementations and adds no mandatory provider or cloud service.
- **Article IV**: PASS — rich treatments use complete provider-native artifacts plus existing thin projections.
- **Article V**: PASS — all content is inert data and parser execution remains bounded/offline.
- **Article VI**: PASS — normative identities use canonical SHA-256 and output publication is atomic.
- **Article VII**: PASS — exact search, bounded context and receipts are tested as delivered.
- **Article VIII**: PASS — negative and integration tests precede the implementation and all full gates remain required.
- **Article IX**: PASS — environment, strong baselines, raw results, limitations and unfavorable outcomes are mandatory.
- **Article X**: PASS — one bounded evaluation slice, no production abstraction or architecture expansion.
- **Article XI**: PASS — isolated branch/PR, full Spec Kit lifecycle and three-platform final quality.
- **Article XII**: PASS — existing release and public compatibility decisions remain authoritative.

### Post-design gate

PASS with no exceptions. The design adds only benchmark-domain records, offline adapters/services, maintainer scripts,
synthetic inputs, tests and evidence. No ADR-triggering storage, identity, schema-compatibility, cloud, embedding or
source-authority decision changes.

## Project Structure

### Documentation (this feature)

```text
specs/020-product-value-benchmark/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── maintainer-benchmark.md
├── checklists/
│   ├── requirements.md
│   └── benchmark-evidence.md
├── analysis.md
├── implementation-notes.md
└── tasks.md
```

### Source Code (repository root)

```text
benchmarks/product-value/v0.1.0/
├── protocol.json
├── corpus-spec.json
├── judgments.json
├── value-policy.json
└── results/reference-macos-arm64/
    ├── observations.json
    ├── summary.json
    ├── decision.json
    ├── run-manifest.json
    └── report.md

src/openardp/
├── domain/product_benchmark.py
└── adapters/product_benchmarks.py

scripts/
├── product_benchmark_evaluation.py
├── generate_product_benchmark.py
├── product_benchmark_runner.py
├── run_product_benchmark.py
└── validate_product_benchmark.py

tests/
├── unit/test_product_benchmark.py
├── integration/test_product_benchmark.py
└── test_product_benchmark_drift.py
```

**Structure Decision**: Reuse the repository's inward dependency direction. Pure closed evidence models and invariants
live in `domain`; deterministic corpus input handling lives in `adapters`; benchmark-only treatment orchestration,
statistics, decisions and projections live in `scripts` so they do not expand the installed runtime service surface.
Normative inputs and the actual reference capture remain inspectable under `benchmarks/`.

## Implementation Phases

### Phase 0 — Freeze methodology

1. Freeze profiles, workloads, metrics, sample rules, resource bounds and sanitization.
2. Freeze value thresholds and three-state decision semantics before measurement.
3. Record strong baselines, limitations and the F015 release-gate separation.

### Phase 1 — Evidence contracts and corpus

1. Add strict internal models and canonical evidence identities.
2. Add deterministic corpus generation for smoke, reference and scale profiles.
3. Add frozen judgments for exact lookup, context budgets and deterministic edits.
4. Add validation and atomic publication boundaries.

### Phase 2 — Treatments and measurement

1. Implement raw text reparsing and persisted parsed-output reuse baselines.
2. Exercise actual OpenARDP text ingestion, status, search, context and replay.
3. Exercise delivered Docling DOCX/PPTX/PDF parsing, native reuse and OpenARDP reuse.
4. Capture monotonic wall time, process CPU, peak-RSS proxy, parser calls, bytes and correctness without bodies.

### Phase 3 — Evaluation and report

1. Validate raw observation completeness and identities.
2. Compute p50, p95, MAD, deterministic bootstrap intervals and break-even counts.
3. Apply frozen policy with stable reasons and no waiver.
4. Generate body-free JSON aggregates and Markdown report deterministically.

### Phase 4 — Reference execution and convergence

1. Run focused negative and smoke tests.
2. Execute the full reference plus 100,000-block profile on the declared host.
3. Commit raw observations and exact report, including failures and unfavorable comparisons.
4. Run complete repository gates, analyze evidence against the spec and converge before protected publication.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
