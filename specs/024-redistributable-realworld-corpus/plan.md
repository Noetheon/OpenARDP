# Implementation Plan: Redistributable Real-World Corpus

**Branch**: `codex/f024-redistributable-realworld-corpus` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

## Summary

Vendor one 6.63 MB, six-format NASA/CISA snapshot with exact byte locks and reviewed rights evidence. Add a closed offline
validator and explicit bounded reproducer. Then execute PDF/DOCX/PPTX through isolated Docling, TXT/Markdown through the
deterministic text parser and CSV through the independent F016 producer, retaining only body-free structural and resource
evidence. CSV uses a dedicated isolated body-free probe because F016's complete-artifact response correctly exceeds its
1 MiB limit on the real catalog. An implementation-independent validator regenerates the fail-closed result. No schema,
storage or default-network behavior changes; the rich adapter gains warning-preserving clipping/pointer fallback for
real provider geometry.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Standard library; existing Pydantic/RFC 8785 identity helpers; existing optional
`docling==2.114.0` profile; isolated stdlib-only body-free CSV probe

**Storage**: About 6.63 MB immutable corpus payload plus small JSON/Markdown review and benchmark evidence in Git; no
workspace migration

**Testing**: pytest, Ruff, strict mypy, repository drift validation, synthetic fetch fault injection, committed corpus
offline validation, opt-in actual PDF reference execution

**Target Platform**: Cross-platform offline corpus verification; binding full parser result on Apple-silicon macOS with
the external F023 bundle

**Project Type**: Additive corpus and maintainer benchmark tooling

**Performance Goals**: corpus validation under 2 seconds and 256 MiB RSS; each rich parse under 120 seconds and 4 GiB
address-space limit; total committed payload under 16 MiB

**Constraints**: no source rewriting, no unit-test network, no hidden fetch, no document content in result artifacts, no
legal or semantic overclaim, no actual model weights in Git

**Scale/Scope**: six files, six formats, two publisher families, two fresh retained parses per file

## Constitution Check

| Article | Design response |
|---|---|
| I Originals | Exact upstream bytes are committed and immutable; conversions cannot satisfy format coverage. |
| II Derived artifacts | Parser/baseline evidence is disposable and independently reproducible. |
| III Interfaces | Existing text, rich and F016 provider boundaries are reused; no new product provider abstraction. |
| IV Offline/local | Validation and parsing are offline; only an explicit maintainer reproducer has egress. |
| V Security | All payload content is untrusted; closed trees, bounded fetches, isolated parsers and body-free errors apply. |
| VI Portability | Corpus identity is path-independent; CI validates bytes and portable parser subsets. |
| VII Observability | Stable IDs, counts and timings are retained without bodies, paths or credentials. |
| VIII Testing | Real redistributable payloads plus synthetic tamper/fetch faults; no network in tests. |
| IX Compatibility | Additive benchmark assets only; no persisted contract or migration change. |
| X Simplicity | Stdlib corpus tooling and existing parser boundaries; no runtime framework added. |
| XI Measured claims | Frozen raw facts and independent validation gate the baseline decision. |
| XII Spec Kit | F024 remains bounded from semantic F025 and completes all lifecycle/release gates first. |

No constitution exception or ADR is required.

## Project Structure

```text
corpora/realworld/v0.1.0/
├── README.md
├── THIRD_PARTY_NOTICES.md
├── corpus-lock.json
├── corpus-lock.schema.json
├── evidence/
│   ├── cisa-kev-revision.json
│   ├── nasa-ntrs-20210012886.json
│   ├── nasa-ntrs-20210014231.json
│   └── nasa-ntrs-20210025005.json
└── sources/
    ├── cisa-kev-license.txt
    ├── cisa-kev-readme.md
    ├── cisa-known-exploited-vulnerabilities.csv
    ├── nasa-ai-strategic-planning-workshop.docx
    ├── nasa-ethical-ai-framework.pdf
    └── nasa-open-science-and-ai.pptx

benchmarks/realworld-corpus/v0.1.0/
├── README.md
├── baseline.json
├── protocol.json
└── results/reference-macos-arm64/...

scripts/
├── realworld_corpus.py
├── fetch_realworld_corpus.py
├── validate_realworld_corpus.py
├── realworld_csv_probe.py
├── realworld_corpus_benchmark.py
├── realworld_corpus_benchmark_evaluation.py
├── run_realworld_corpus_benchmark.py
└── validate_realworld_corpus_benchmark.py
```

Tests are split across unit contract/fault cases, security tree/network cases, integration producer/validator independence,
actual-reference opt-in coverage and committed-result drift checks.

## Implementation Phases

1. Freeze the six exact source inputs and retained publisher/revision evidence.
2. Specify the lock/schema/identity and closed-tree invariants with tests before implementation.
3. Implement the offline producer-side verifier and explicit atomic connected reproduction.
4. Add an independent offline validator that does not import producer code.
5. Define the versioned parser baseline protocol, thresholds and body-free observation contract.
6. Implement five delivered parser paths plus the bounded CSV probe and pure result evaluation, then an independent
   result validator.
7. Reproduce twice, execute the binding baseline with the F023 bundle and commit exact validated evidence.
8. Synchronize documentation and repository inventories; run convergence, full local gates and private three-platform PR.

## Complexity Tracking

No constitutional violation. Committing 6.63 MB of exact source bytes is intentional: a corpus that requires a live host
is neither offline nor independently inspectable. The benchmark-only CSV probe is deliberately not promoted into the
core parser contract. A separate validator duplicates narrow parsing/decision logic so generated claims are not
self-attested.

## Rollback

Revert the feature commit/merge. No workspace, database, runtime configuration or persisted identifier migration exists.
The corpus and all baseline results are additive benchmark data.
