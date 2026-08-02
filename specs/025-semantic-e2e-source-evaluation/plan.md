# Implementation Plan: Semantic End-to-End Source Evaluation

**Branch**: `codex/f025-semantic-e2e-source-evaluation` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

## Summary

Add a frozen, independently validated benchmark that runs nineteen realistic questions through exact F024/F023-backed
OpenARDP ingestion and context compilation. Compare untouched questions with pre-frozen manual lexical terms, evaluate
answer-support/citations/source fitness, retain unsupported CSV/language/abstention gaps and emit an honest three-state
semantic-readiness decision without adding a model or new product API.

## Technical Context

**Language/Version**: Python 3.12
**Environment**: `uv sync --locked --all-extras`; committed `uv.lock` unchanged
**Core dependencies**: existing Pydantic v2, SQLite/CAS, Docling 2.114.0 and stdlib; no new dependency
**Storage**: temporary fresh local workspaces plus body-free JSON result under `benchmarks/semantic-e2e/v0.1.0/`
**Testing**: pytest, Ruff, strict mypy, repository validator, build, pre-commit
**Binding inputs**: F024 corpus v0.1.0 and external F023 model bundle
**Resource bounds**: 30 minutes, 4 GiB address space, 2 GiB workspace, 16 MiB result
**Network**: denied during every benchmark/test/validation operation

## Constitution Check

| Principle | Plan response | Gate |
|---|---|---|
| Originals authoritative | Read exact F024 payloads; never modify or convert them into claimed product support. | PASS |
| Derived disposable | Questions/results are versioned benchmark evidence and can be regenerated. | PASS |
| No universal vectors | No embedding/vector dependency or semantic-equivalence claim. | PASS |
| Progressive disclosure | Use delivered bounded context and body-free receipts before exact evaluation reads. | PASS |
| Untrusted content | Questions and documents remain data; no content-triggered tools or network. | PASS |
| Provider-neutral core | No core provider API change; benchmark consumes existing interfaces. | PASS |
| Local-first | Binding run is offline; the PDF bundle is explicit local input. | PASS |
| Determinism first | Exact atoms, canonical JSON, integer metrics and independent validation. | PASS |
| Measure claims | Frozen thresholds precede the run; negative/conditional output is valid. | PASS |
| Small PR | F025 contains benchmark/evidence only; follow-up semantic capability is excluded. | PASS |
| Contract evolution | No stable schema or persisted identifier changes. | PASS |
| Spec Kit | Full lifecycle and convergence precede publication. | PASS |

## Architecture and Data Flow

```text
F024 exact sources + F023 bundle
              |
              v
    fresh SQLite/CAS workspace
       | text ingest | rich ingest
              v
 verified snapshot of five product-supported assets
              |
      +-------+------------------+
      |                          |
 untouched question       frozen operator terms
      |                          |
      +------ ContextCompiler ---+
                    |
          verified ContextBundle
                    |
      atom/source/citation evaluator
                    |
        body-free raw observations
                    |
         pure summary + decision
                    |
       independent stdlib validator
```

CSV atoms are verified by the exhaustive benchmark oracle but produce declared product `unsupported_format` rows. The
oracle never injects CSV rows into the product workspace.

## Project Structure

```text
benchmarks/semantic-e2e/v0.1.0/
├── README.md
├── protocol.json
├── questions.json
├── questions.schema.json
└── results/reference-macos-arm64/
    ├── decision.json
    ├── observations.json
    ├── report.md
    ├── run-manifest.json
    └── summary.json

scripts/
├── semantic_e2e_benchmark.py
├── semantic_e2e_evaluation.py
├── run_semantic_e2e_benchmark.py
└── validate_semantic_e2e_benchmark.py

tests/
├── unit/test_semantic_e2e_benchmark.py
├── integration/test_semantic_e2e_benchmark.py
├── integration/test_semantic_e2e_reference.py
└── test_semantic_e2e_drift.py
```

No new module is added under `src/openardp`; the benchmark composes existing public services and adapter ports.

## Implementation Phases

### Phase A — Frozen contracts and test fixtures

1. Commit closed protocol/question schemas and all nineteen reviewed questions/atoms/source fitness facts.
2. Add producer and independent-validator tests for canonical identity, closed coverage, normalization and tampering.
3. Add pure evaluation fixtures that prove READY, CONDITIONAL and NOT_READY branches before real execution.

### Phase B — Product-path producer

1. Validate exact F024 corpus and F023 installation.
2. Create one fresh workspace and deterministically ingest TXT/MD plus PDF/DOCX/PPTX.
3. Verify oracle atoms against all extracted evidence and CSV rows.
4. Compile direct/operator contexts with identical fixed limits.
5. Re-resolve selected items, map them to asset keys and emit body-free observations.
6. Repeat in a second fresh workspace and require identical semantic identities/judgments.

### Phase C — Independent result boundary

1. Summarize exact integer numerators/denominators and apply pre-run policy.
2. Publish five result files atomically with bounded size and sanitized failures.
3. Independently parse raw files, recompute coverage/metrics/decision/report/hashes and reject disagreement.

### Phase D — Binding evidence and convergence

1. Run the exact real corpus twice with sockets denied and the validated external bundle.
2. Independently validate and commit the body-free result, including unfavorable rows.
3. Document representative successes/failures, interpretation and concrete follow-up options.
4. Run all local gates, Spec-Kit analysis/convergence and private release workflow; retain GitHub billing limits exactly.

## Risk Controls

- **Post-hoc benchmark tuning**: protocol/questions/threshold tests are committed before the first binding run.
- **Circular scoring**: support atoms and source roles are fixture inputs; evaluator never writes them.
- **Producer-validator coupling**: validator is stdlib-only and imports neither producer nor evaluator.
- **Body leakage**: result schema contains IDs/counts/booleans only; security tests scan forbidden fields and corpus text.
- **CSV overclaim**: explicit `unsupported_format` rows and documentation; no conversion path.
- **Model/network drift**: F023 exact verification, socket denial and stable error categories.
- **Nondeterministic IDs**: compare source/evidence identities and normalized semantic observations, not random workspace IDs.
- **Ground-truth error**: exhaustive atom existence gate plus human-readable reference answers and source pointers.
- **Cost regression**: actual PDF run is opt-in; routine CI validates frozen results with miniature fixtures.

## Complexity Tracking

No constitutional violation or ADR-requiring change is planned. The separate operator treatment is additional benchmark
complexity justified by the need to distinguish current product capability from manual query assistance.
