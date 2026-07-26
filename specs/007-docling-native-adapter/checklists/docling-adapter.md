# Requirements Quality Checklist: Docling Native Adapter

**Purpose**: Challenge completeness, clarity, consistency and measurability of F007
requirements before tasks and implementation

**Created**: 2026-07-26

**Feature**: [spec.md](../spec.md)

## Scope and provider boundary

- [x] CHK001 Are PDF, DOCX and PPTX the only accepted provider formats?
- [x] CHK002 Is the provider optional without making F006 consumption optional?
- [x] CHK003 Are OCR, captions, remote services, alternate parsers and later features explicitly excluded?
- [x] CHK004 Is a second complete OpenARDP rich-document model explicitly prohibited?
- [x] CHK005 Are provider/runtime objects prohibited from public contracts and port results?

## Native representation and reproducibility

- [x] CHK006 Is “complete native representation” defined as one exact lossless provider export profile?
- [x] CHK007 Are conversion telemetry, host facts and local paths excluded from native evidence?
- [x] CHK008 Are provider, component, profile, config, model and artifact identities required?
- [x] CHK009 Are timestamps and nondeterminism observations separated from content identity?
- [x] CHK010 Is changed provider/config/model identity guaranteed to prevent incompatible reuse?

## Thin evidence projection

- [x] CHK011 Are text, heading, table-cell, page/picture and opaque-pointer cases covered?
- [x] CHK012 Is the provider-profile text view deterministic and bounded?
- [x] CHK013 Are coordinate-origin, finite-value, clipping and fixed-point conversion rules required?
- [x] CHK014 Are table indices/spans and parent ordering validated before F006 construction?
- [x] CHK015 Do unknown provider labels remain native rather than gain guessed neutral semantics?
- [x] CHK016 Are retrieval bodies immutable, typed, bounded and digest-verified?
- [x] CHK017 Must all F006 record and aggregate invariants pass before READY?

## Trust and pointer safety

- [x] CHK018 Is all document/provider content data-only and non-executable?
- [x] CHK019 Is effective trust prohibited from exceeding source origin trust?
- [x] CHK020 Are pointers explicitly profile/version/native scoped?
- [x] CHK021 Is pointer grammar bounded and independent of filesystem/URI/import semantics?
- [x] CHK022 Does pointer resolution traverse only already parsed safe JSON?
- [x] CHK023 Are wrong-profile, malformed, unsafe and missing pointers distinguishable?

## Worker isolation and limits

- [x] CHK024 Must the worker use spawn and be killable on all supported platforms?
- [x] CHK025 Is network denial applied before provider import and paired with offline flags?
- [x] CHK026 Is the absence of source-path authority testable?
- [x] CHK027 Does every resource/output limit state units, default, range and failure category?
- [x] CHK028 Are POSIX-only controls distinguished from portable controls?
- [x] CHK029 Is the boundary described as defense-in-depth rather than a strong sandbox?
- [x] CHK030 Are IPC payloads strict, bounded and free of arbitrary exception/object transport?

## Failure, cancellation and cleanup

- [x] CHK031 Are timeout, crash, cancellation, malformed/partial output and network attempts covered?
- [x] CHK032 Are source/page/native/projection/retrieval excesses covered separately?
- [x] CHK033 Are disk exhaustion and atomic-publication failures acceptance concerns?
- [x] CHK034 Must every exit close IPC and terminate background work?
- [x] CHK035 Must every failure preserve originals and prevent incomplete READY state?
- [x] CHK036 Are diagnostics stable, sanitized and body/path-free?
- [x] CHK037 Is durable queued-job cancellation explicitly deferred to F012?

## Persistence, reuse and migration

- [x] CHK038 Does rich persistence reuse the existing representation lease/head/event lifecycle?
- [x] CHK039 Is migration 5 additive, checksummed, transactional and restart-safe?
- [x] CHK040 Are every descriptor/native/bundle/record/retrieval object reachable from catalog facts?
- [x] CHK041 Is one transaction required for rich rows, READY state, head and success event?
- [x] CHK042 Is complete authoritative cache verification required before parser-free reuse?
- [x] CHK043 Are force, changed bytes, changed recipe, content convergence and nondeterminism defined?
- [x] CHK044 Is rollback after workspace migration defined through backup/restore rather than in-place editing?

## Dependency, models and platform quality

- [x] CHK045 Is the exact provider version tied to maintenance, license, provenance and advisory review?
- [x] CHK046 Are model licenses and files reviewed independently of Docling's code license?
- [x] CHK047 Does PDF fail before provider execution when the local bundle is absent or drifted?
- [x] CHK048 Are model manifests path-confined, link-safe, digest-complete and path-independent in identity?
- [x] CHK049 Must actual DOCX/PPTX provider smoke tests run in the locked environment?
- [x] CHK050 Is the PDF no-assets path mandatory while model-backed execution remains conditional on reviewed assets?
- [x] CHK051 Does Linux/macOS/Windows CI install all extras and exercise worker/packaging behavior?

## CLI, privacy and compatibility

- [x] CHK052 Does existing text ingest retain its behavior and output compatibility?
- [x] CHK053 Are rich ingest, evidence listing and exact one-body retrieval independently demonstrable?
- [x] CHK054 Are URLs, arbitrary headers and automatic downloads excluded from CLI configuration?
- [x] CHK055 Are logs/errors/catalog failures prohibited from exposing bodies, credentials and absolute paths?
- [x] CHK056 Must all nine public schemas and both identity vector sets remain byte-identical?
- [x] CHK057 Must the established F006 conformance corpus continue to pass unchanged?
- [x] CHK058 Are new application/workspace/provider versions kept independent of the F006 contract version?
- [x] CHK059 Are exact local/remote commands, limits, residual risks and rollback evidence required?
- [x] CHK060 Are parse-throughput and strong-sandbox claims explicitly withheld without evidence?

## Resolution notes

- All 60 questions are answered by `spec.md`, `research.md`, `data-model.md`,
  `contracts/docling-adapter.md`, accepted ADRs or the constitution.
- No unresolved clarification or blocking requirement-quality defect remains.
