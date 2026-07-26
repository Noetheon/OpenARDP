# Implementation Notes: Docling Native Adapter

**Feature**: `007-docling-native-adapter`

**Branch**: `codex/f007-docling-native-adapter`

**Date**: 2026-07-26

## Acceptance criteria restatement

- Ingest local PDF/DOCX/PPTX through one exactly locked optional Docling provider.
- Retain complete immutable provider-native JSON and emit only F006 thin evidence.
- Run in a spawned bounded, network-denied, path-free worker without a universal sandbox
  claim.
- Reuse unchanged exact work only after full CAS/catalog/F006 validation.
- Fail closed on missing PDF assets, malformed/partial output, timeout, crash,
  cancellation, resource/output limits and storage failure.
- Preserve existing source files, text ingestion, search, public schemas and identity
  vectors.
- Pass the complete locked gate and Linux/macOS/Windows CI before merge.

## Frozen baseline

- Base commit: `a232e0715a8ac7cb32895710ee327e6cf3b1db95`.
- Python: CPython 3.12.13 on macOS.
- Source modules: 33.
- `uv run --locked ruff check .`: pass.
- `uv run --locked ruff format --check .`: pass; 71 files.
- `uv run --locked mypy src`: pass.
- `uv run --locked pytest`: 476 passed; 86.69% branch coverage.
- Schema drift check: all 9 schemas current.
- Evidence conformance: 7 valid, 8 invalid, 1 record set, 6 identity vectors.
- Repository validation: pass.

### Frozen public artifact hashes

| Artifact | SHA-256 |
|---|---|
| `block.schema.json` | `413d725016a9f4f261e384efff3f82906a08c7e3b73a25bc8f96963a10861562` |
| `context-bundle.schema.json` | `e6cea129f58bd11ec52e1f63ef87258d8ec9c01ac37ff7fa933b08e96790a31a` |
| `derivation.schema.json` | `56e8fc17050584b6d4bfc430d5f8d24de03237e5ef2b96fc7d9f6afd61f3e88a` |
| `evidence-projection.schema.json` | `cc580d589e46142a6c8429e0deb855c1bf3be79cf4334d9b39129e46c80aaf1e` |
| `evidence-reference.schema.json` | `b86968eca4d9a8c208c4a4f52f207dda863377dcc5bf353775b0067e2b4f4362` |
| `manifest.schema.json` | `1995cc1062e5322405a00adba8e47c7f3bed9fa294de6920dc27476c5a36dfd4` |
| `native-representation.schema.json` | `c4685f98633f2628240059e55703a0d8f27e32eb549cd7d453deb91b23d4d6ef` |
| `relation.schema.json` | `00b581b077089e6534f4cc0c3af511fa2caa8ede6b81649ee5094f0b60bca142` |
| `trust-classification.schema.json` | `7c4a7b429a3994ebd62af394b06cf7daaeeb691720778ef0122c1871fff302bc` |
| F006 identity vectors | `da1c718da44c6e51f3ec2e7aafcd94de4b59dad8b3c02e442eb02527a8729e97` |
| F002 identity vectors | `9387f64d8cf90f2039ca975c71d6f02d57cef8027005b69da6e07b4f8b6c291b` |

## Test-first evidence

### Phase 1 — dependency boundary

Before `pyproject.toml` or `uv.lock` changed, the new dependency contract test produced
two intended failures: the optional dependency table was absent and Docling distribution
metadata was unavailable. The independent lazy-import assertion already passed. After
locking the extra, all three focused tests pass.

- Lock resolution: 143 packages.
- Reviewed installed components: Docling 2.114.0, docling-slim 2.114.0,
  docling-core 2.87.1, docling-parse 7.8.1, docling-ibm-models 3.13.3 and
  torch 2.13.0.
- Fresh offline core-only wheel environment installed seven packages and reported
  `0.0.1 core_without_docling`.
- The all-extras environment reports the exact reviewed provider release while importing
  `openardp` alone loads no `docling` module.

### Phase 2 — provider-neutral contracts

Before implementation, the focused collection failed because
`openardp.domain.rich_ingestion` and the rich parser port taxonomy did not exist. The
red run produced three expected collection errors while the already-implemented local
text tests remained collectable. After implementation:

- source snapshots accept only TXT/Markdown/PDF/DOCX/PPTX, while
  `ParsedTextDocument` remains restricted to `TextMediaType`;
- model manifests enforce bounded sorted relative POSIX paths, exact SHA-256/length
  facts, reviewable license values, namespaced safe JSON and a path-independent RFC
  8785 identity;
- the rich recipe aligns the existing representation recipe with the unchanged F006
  provider recipe;
- native descriptors, evidence records/bundles, canonical/converged/diverged attempts
  and bounded results validate exact source/native/object scope before I/O;
- `RichCatalog` extends the existing `Catalog` protocol additively, so current text
  consumers remain structurally compatible until migration 5 is implemented;
- rich parser errors and protocols contain no Docling runtime type or import.

Observed green evidence:

- focused F007 Phase 1/2 and package surface: 55 passed in 1.63 seconds;
- full repository regression suite: 502 passed in 20.21 seconds;
- full branch coverage: 85.58%, above the required 85%;
- Ruff check, Ruff format check and strict mypy over 34 source modules: pass.

### Phase 3 — native conversion, isolation and F006 construction

The initial tests failed because no native adapter, worker boundary, deterministic rich
fixtures or F006 construction service existed. The implementation then added:

- reproducible DOCX/PPTX ZIP normalization plus a hand-authored deterministic PDF;
- exact Docling 2.114.0 component checks and a closed offline recipe;
- local declarative DOCX/PPTX backends that avoid instantiating the PDF/ML pipeline;
- a configured PDF path that requires a validated local model bundle before provider
  import or conversion;
- spawned, path-free byte streaming with socket denial, portable resource limits,
  bounded IPC and terminate/kill/reap cleanup;
- complete native JSON retention, deterministic thin evidence projection, fixed-point
  coordinates and bounded RFC 6901 reference resolution;
- CAS-backed construction of strict F006 native/reference/projection/trust/retrieval
  records and one immutable evidence-bundle root.

Actual provider inspection exposed one upstream interoperability edge: Docling exports
`origin.binary_hash` as an unsigned 64-bit integer that can exceed the I-JSON/JCS safe
integer range. The originating spec, research, data model, contract and plan now permit
lossless decimal-string normalization for that exact field only; all other unsafe
numbers remain rejected. The adapter emits
`provider_binary_hash_stringified` when this normalization occurs.

Model-bundle verification streams each regular file through SHA-256 in 1 MiB chunks,
checks declared length while reading and compares the opened inode/device to the
reviewed `lstat` result. It therefore avoids loading large model assets into memory and
fails closed on missing, substituted, non-regular or symlinked content.

Observed green evidence:

- independent US1/security suite: 58 passed in 7.94 seconds;
- actual DOCX: 2 text nodes, 0 pages;
- actual PPTX: 3 text nodes, 2 pages;
- PDF without local assets: typed `model_assets_required` before provider execution;
- full repository suite: 530 passed in 26.28 seconds;
- full branch coverage: 85.08%, above the required 85%.

Exact installed runtime components:

| Distribution | Version |
|---|---|
| `docling` | `2.114.0` |
| `docling-core` | `2.87.1` |
| `docling-ibm-models` | `3.13.3` |
| `docling-parse` | `7.8.1` |
| `docling-slim` | `2.114.0` |
| `torch` | `2.13.0` |

### Phase 4 — atomic persistence, verified reuse and immutable drift

Migration 5 adds three narrow, additive catalog structures: append-only rich attempts,
their complete evidence-object inventory and one accepted-attempt link per exact
representation scope. All earlier migration statements and checksums remain unchanged.
A real revision-4 database upgrades transactionally to revision 5; incompatible,
checksummed, rollback and newer-reader protections continue to pass.

The catalog's existing READY transaction is reused through a caller-owned transaction
boundary. Consequently, base manifest/source facts, accepted rich linkage, attempt and
evidence rows, document head and ingestion event either all become visible or all roll
back. An injected failure after evidence insertion leaves the representation STAGING
and exposes no rich attempt.

Every successful forced parse is durable. Semantic equality across provider-native,
native-representation, reference, projection and retrieval identities produces a
`CONVERGED` attempt. A valid difference produces `DIVERGED`; it remains fully reachable
but cannot replace the canonical accepted attempt or advance the head. Attempt UUID
replay is idempotent only for byte-for-byte equivalent immutable facts.

Cache reuse verifies the source, manifest, descriptor, complete provider-native JSON,
F006 native record, evidence bundle, every reference/projection record and every
retrieval artifact before appending `CACHE_HIT`. Ten consecutive exact repeats invoke
the parser zero additional times. Changed bytes and changed recipe/model-bundle identity
each produce a new exact representation. Fault injection over all nine base/rich object
classes fails closed before cache acceptance.

Observed green evidence:

- US2 migration/catalog/service/reachability suite: 58 passed in 1.40 seconds;
- complete repository suite: 555 passed in 28.15 seconds;
- full branch coverage: 85.17%;
- Ruff check, Ruff format check and strict mypy over 37 source modules: pass.

### Phase 5 — bounded failure and publication safety

The hostile-path matrix now exercises timeout, hard child exit, result-pipe closure,
input-stream failure, cancellation, provider exception, network attempt, dependency
drift, malformed/partial output categories and every configured output bound. A
two-slide PPTX under a one-page limit is rejected as a resource failure rather than
silently truncated. Timeout cleanup, including child reap, completes within the
specified five-second ceiling.

Worker exception text, source paths, document bodies and tracebacks never cross the IPC
allowlist. The parent receives only stable machine categories and bounded generic
messages. The same redaction applies to malformed native values and storage failures.

Initial CAS publication and injected catalog-commit failures transition the fenced base
representation to retryable `FAILED`, expose no rich READY aggregate and succeed on a
subsequent claim with incremented attempt count. A parser failure during forced reparse
leaves the already accepted attempt, head and attempt inventory unchanged. Pre-commit
CAS objects may remain immutable and unreachable, as documented for later F013
retention/recovery.

Observed green evidence:

- US3 worker/provider/storage failure matrix: 50 passed in 11.4 seconds;
- no child-process delta after timeout, crash, IPC close or cancellation;
- all default errors remained body-, path- and traceback-free.

### Phase 6 — provider-free evidence inspection and CLI

`RichEvidenceService` loads one accepted catalog snapshot, runs complete base/rich
verification, lists only F006 projection metadata, retrieves one explicitly selected
UTF-8 body by exact digest and exposes complete native JSON only through an object-scoped
programmatic method. Pointer resolution checks provider profile, independent profile
version and RFC 6901 format before resolving a bounded value solely inside retained
native JSON. No Docling type or import is required.

The CLI now routes rich suffixes explicitly while preserving the prior text path and
output. DOCX/PPTX use the exact adapter profile; PDF accepts only a local model root plus
a strict local manifest, never a URL. Manifest reading uses a bounded no-follow file
descriptor and inode/device comparison. `evidence` is body-free; `get-evidence` returns
one intentional verified body. JSON and human modes use the existing stable envelopes
and sanitized error classes.

Observed green evidence:

- US4 service/CLI/pointer/package and prior text CLI suite: 44 passed in 7.13 seconds;
- actual CLI DOCX initial parse plus verified cache repeat: pass;
- PDF missing-assets CLI gate: stable `rejected_input`;
- existing text CLI JSON/human snapshots: pass unchanged.

## Initial Spec Kit analysis

The first pass checked 33 functional requirements, 12 measurable success criteria, four
independently testable user stories, 69 implementation tasks, 12 constitution articles,
and 76 completed requirements-quality checks.

It found one HIGH design contradiction: valid nondeterministic forced-reparse output
could not overwrite the immutable accepted representation but the original design had no
durable alternative. The originating specification, research, data model, adapter
contract, plan and tasks now require append-only canonical/converged/diverged
`RichParseAttempt` records while preserving the accepted READY representation and head.
The same correction clarified native-only zero-evidence outcomes. A second analysis pass
found no unresolved critical or high finding and no uncovered requirement.

## Validation

The final local gate ran from the exact locked feature tree on macOS with CPython
3.12.13:

| Command/evidence | Result |
|---|---|
| `uv run --locked ruff check .` | pass |
| `uv run --locked ruff format --check .` | pass; 90 files |
| `uv run --locked mypy src` | pass; 38 source files |
| `uv run --locked mypy src --platform win32` | pass; 38 source files |
| `uv run --locked pytest` | 566 passed in 41.16 seconds; 85.36% branch coverage |
| `uv run --locked python scripts/generate_schemas.py --check` | all 9 schemas current |
| `uv run --locked python scripts/validate_evidence_contracts.py conformance/evidence/v0.1.0/manifest.json` | 7 valid, 8 invalid, 1 record set, 6 identity vectors |
| `uv run --locked python scripts/validate_repository.py` | pass |
| `git diff --check` | pass |
| `uv build` | source distribution and wheel built |

Byte comparison against base
`a232e0715a8ac7cb32895710ee327e6cf3b1db95` found no change in any of the nine
public schema JSON files, either canonicalization-vector file, or the complete F006
conformance corpus. Their frozen hashes remain those recorded above.

Fresh isolated wheel probes established both packaging boundaries:

- the core wheel installed seven packages, imported all intentional core
  adapters/services/CLI surfaces, reported OpenARDP `0.0.1`, and had no `docling`
  distribution or loaded module;
- the rich wheel installed 103 packages and resolved exactly Docling `2.114.0`,
  docling-core `2.87.1`, docling-slim `2.114.0`, docling-parse `7.8.1`,
  docling-ibm-models `3.13.3`, and torch `2.13.0`;
- the installed rich console ingested the reviewed DOCX and PPTX fixtures with actual
  provider execution, produced 6 and 9 evidence projections respectively, reused the
  unchanged DOCX as `CACHE_HIT` without invoking the parser, and recorded an explicit
  forced reparse as `CONVERGED`;
- the installed console rejected PDF without reviewed local model assets before
  provider execution using the stable `rejected_input` envelope.

The final Spec Kit analysis again mapped all 33 functional requirements, 12 success
criteria and four independently testable stories to the 69 tasks and implementation
evidence. No unresolved critical/high contradiction, uncovered requirement, ambiguous
normative term, or constitution violation remained. Convergence found no additional
task to append.

## Tradeoffs and residual risks

- The spawned worker, socket denial, offline environment, portable time/output limits
  and POSIX resource limits are defense-in-depth, not an operating-system sandbox.
- Actual provider conversion was exercised for DOCX and PPTX. PDF was intentionally
  verified at its missing-assets fail-closed boundary because no separately reviewed,
  license-approved local model bundle was placed in scope.
- Docling's complete native graph and provider outputs can change across provider
  upgrades or platforms. The exact provider/component/profile/recipe identities and
  append-only divergence attempts make that nondeterminism visible; they do not claim
  universal bit-for-bit parser determinism.
- The exact DOCX/PPTX backend seam uses the reviewed Docling `2.114.0` internal
  `InputDocument` backend. Every provider upgrade therefore requires renewed contract,
  fixture, supply-chain and three-platform review rather than an automatic version bump.
- The optional rich dependency graph is intentionally large (103 packages in the fresh
  wheel probe). Core consumers retain the seven-package provider-free installation.
- Docling code is MIT-licensed in the reviewed publication metadata; separately
  provisioned PDF model files retain their own operator-reviewed licenses and are not
  fetched or redistributed.
- Catalog revision 5 is forward-only for this release. Older readers require a
  revision-4 backup; unreachable immutable CAS objects from failed pre-commit
  publication remain until F013 retention/recovery work.
- The local evidence supports correctness, isolation boundaries and reuse behavior, not
  universal performance, security, parser-quality or cross-document completeness
  claims. Linux/macOS/Windows remote evidence remains pending until publication.

## Rollback

The implementation commit can be reverted before a workspace is opened at catalog
revision 5. After migration/use, restore a revision-4 backup to run older software;
never edit migration history or downgrade a live catalog in place. CAS objects are
immutable and may remain unreachable until F013 recovery/retention tooling.

## Remote verification

- Local feature commit:
  `ee4ba2511975fa5fb3d2e3dc022ba82b5cb82249`.
- Pull request:
  [#10](https://github.com/Noetheon/OpenARDP/pull/10), merged 2026-07-26.
- Squash commit on `main`:
  `1a080d37efcc2f74307bb01a6656db09659e9138`.
- PR-head Linux/macOS/Windows workflow:
  [30208533025](https://github.com/Noetheon/OpenARDP/actions/runs/30208533025),
  all three quality jobs passed against the exact feature commit.
- Post-merge `main` Linux/macOS/Windows workflow:
  [30208840651](https://github.com/Noetheon/OpenARDP/actions/runs/30208840651),
  all three quality jobs passed against the exact squash commit.
