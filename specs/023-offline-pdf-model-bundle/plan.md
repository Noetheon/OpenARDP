# Implementation Plan: Offline PDF Model Bundle

**Branch**: `codex/f023-offline-pdf-model-bundle` | **Date**: 2026-08-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/023-offline-pdf-model-bundle/spec.md`

## Summary

Close the only missing F007 rich-format runtime boundary by pinning the two upstream repositories used by the exact
Docling `2.114.0` PDF profile, provisioning their five required files into a closed local tree, generating the existing
canonical model manifest, and packaging the installation deterministically for offline transfer. Validation becomes
closed-tree rather than listed-file-only. A versioned benchmark then proves actual PDF conversion with empty caches and
sockets denied and publishes bundle size, validation, conversion, memory, output and correctness evidence.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Pydantic v2 and RFC 8785 core; exact optional `docling==2.114.0` stack including
`huggingface-hub==1.24.0`; Python standard-library hashing, ZIP and resource/process facilities

**Storage**: Immutable regular-file bundle outside Git; canonical JSON source lock/manifest and body-free benchmark JSON
inside Git; no workspace/catalog migration

**Testing**: pytest with socket denial and branch coverage, synthetic miniature bundle/archive fixtures in ordinary CI,
actual heavyweight local reference capture, Ruff, strict mypy and deterministic independent validators

**Target Platform**: Linux, macOS and Windows semantics; binding heavyweight measurement on Apple-silicon macOS

**Project Type**: Python library/CLI plus explicit maintainer provisioning and benchmark scripts

**Performance Goals**: installed runtime assets at most 450 MiB; validation p95 at most 5 seconds and 512 MiB RSS; each
frozen synthetic-PDF conversion within the existing 120-second/4-GiB worker bounds

**Constraints**: no implicit download, model weights in Git, global-cache fallback, remote service, OCR/enrichment,
unbounded extraction or body/path leakage; actual CI remains network-free and does not download heavyweight assets

**Scale/Scope**: two immutable upstream repositories, five runtime files, two reviewed licenses, one deterministic ZIP
profile, one frozen synthetic PDF and at least three accepted fresh-worker conversions

**Contract/Version Impact**: additive source-lock/package/benchmark contracts and stricter interpretation of the existing
`ModelBundleManifest`; application and workspace revisions unchanged; provider profile remains
`openardp-docling-native/0.1.0` because the recipe already binds `model_bundle_id`; export profile unaffected

**Trust/Operational Impact**: only explicit provisioning has egress. Downloads are untrusted until size/digest/license
lock verification and atomic publication. Offline verification and conversion deny links, extra files, cache authority,
sockets and provider-side remote services. Model content remains untrusted data and never initiates tools.

## Constitution Check

*GATE: passed before research and re-checked after design.*

| Article | Design evidence | Result |
|---|---|---|
| I Source Truth | Existing PDF source bytes and historical F020 evidence remain unchanged | PASS |
| II Disposable Derivations | Bundle is reproducible from immutable source locks and not workspace authority | PASS |
| III Implementation First | Extends the delivered F007 Docling adapter rather than inventing another parser | PASS |
| IV Thin Projection | Complete Docling native JSON and existing thin projections remain the evidence boundary | PASS |
| V Data Is Not Instruction | Model bytes/metadata cannot run tools; paths and archive members use closed validation | PASS |
| VI Determinism | Full SHA-256 inventory, RFC 8785 bundle ID, deterministic package and atomic publication | PASS |
| VII Progressive Context | No context or semantic expansion; F025 remains separate | PASS |
| VIII Test-First Gates | Failure-first fixture tests precede provisioning/package/parser changes; full gates required | PASS |
| IX Measured Claims | Frozen offline benchmark, independent validator and honest not-ready outcome are binding | PASS |
| X Simplicity | Five required files only; disabled OCR/enrichment models are not downloaded | PASS |
| XI Feature Isolation | F024/F025 excluded; one branch/PR and three-platform ordinary gates | PASS |
| XII Contract Evolution | Existing identity retained; additive contracts documented and checked for compatibility | PASS |

Post-design re-check: PASS. The one intentional network-capable component is an explicit provisioning adapter/script,
never imported by ordinary startup or conversion, and therefore satisfies the constitution's explicit-egress exception.

## Project Structure

### Documentation (this feature)

```text
specs/023-offline-pdf-model-bundle/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── implementation-notes.md
├── contracts/
│   └── offline-pdf-bundle.md
├── checklists/
│   ├── requirements.md
│   └── supply-chain.md
└── tasks.md
```

### Runtime, assets and evidence

```text
model-bundles/pdf-docling-2.114.0-v1/
├── README.md
├── source-lock.json
├── manifest.json
├── THIRD_PARTY_NOTICES.md
└── licenses/
    ├── Apache-2.0.txt
    └── CDLA-Permissive-2.0.txt

src/openardp/adapters/
├── docling_bundle.py
├── docling_bundle_archive.py
├── docling_bundle_provisioning.py
└── docling_native.py

scripts/
├── provision_pdf_bundle.py
├── verify_pdf_bundle.py
├── package_pdf_bundle.py
├── install_pdf_bundle.py
├── run_pdf_bundle_benchmark.py
├── pdf_bundle_benchmark.py
├── pdf_bundle_benchmark_evaluation.py
└── validate_pdf_bundle_benchmark.py

benchmarks/pdf-bundle/v0.1.0/
├── README.md
├── protocol.json
├── baseline.json
└── results/reference-macos-arm64/

tests/
├── contract/test_pdf_bundle_contract.py
├── integration/test_pdf_bundle_lifecycle.py
├── integration/test_pdf_bundle_reference.py
├── security/test_pdf_bundle_boundaries.py
├── unit/test_docling_bundle.py
└── unit/test_pdf_bundle_benchmark.py
```

**Structure Decision**: Closed-tree contracts/verification, online provisioning and portable archive handling are three
narrow provider-adapter modules with no domain-to-adapter imports. Thin scripts are explicit trusted composition roots.
The large assets and generated package live outside Git; committed locks, notices and reference measurements remain small
and inspectable. Benchmark execution, evaluation/projection and independent validation are separated under `scripts/`,
following the F020/F022 maintainability boundary without repeating its oversized-runner debt.

## Design Phases

### Phase A — Tests and immutable inputs

Freeze source revisions, file mapping, licenses and package limits. Add miniature fixtures covering exact success plus
every download/tree/archive failure before changing validation behavior.

### Phase B — Provision, verify, package and install

Implement streamed pinned retrieval, deterministic manifest/provenance materialization, closed-tree validation, atomic
directory publication, deterministic ZIP creation and bounded safe extraction. Keep remote imports lazy and command-only.

### Phase C — Real PDF proof and benchmark

Provision the exact bundle into an external reference root, build/install its portable package in a fresh path, parse the
frozen PDF with empty caches and socket denial, retain raw observations, independently regenerate summaries/decision and
commit only body-free evidence.

### Phase D — Convergence and release

Run quickstart, full local quality/repository/package gates, Spec-Kit convergence, private PR, trusted Linux/macOS/Windows
ordinary CI, merge and post-merge verification before activating F024.

## Complexity Tracking

No constitution violation requires justification. ZIP is selected over a custom binary container because the standard
library supports deterministic construction and every accepted member is independently reconciled to the closed manifest.
