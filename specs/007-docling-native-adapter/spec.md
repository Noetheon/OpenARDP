# Feature Specification: Docling Native Adapter

**Feature Branch**: `codex/f007-docling-native-adapter`

**Created**: 2026-07-26

**Status**: Locally converged; remote verification pending

**Input**: Ingest local PDF, DOCX, and PPTX through a bounded Docling worker,
preserve the complete provider-native representation immutably, and emit the
Feature 006 thin evidence contracts without introducing a second rich-document
model.

## Clarifications

### Session 2026-07-26

- Q: Is rich-parser support part of the mandatory lightweight core installation?
  → A: No. It is an explicitly installed, exactly locked optional capability; the core
  and F006 contract consumer remain usable without importing the provider.
- Q: May PDF ingestion fetch model files automatically?
  → A: No. PDF pipelines that require model files accept only a validated local,
  path-confined model bundle. Missing or drifted assets fail before provider execution.
- Q: What is retained as the complete native representation?
  → A: The provider's complete document model is exported with a versioned,
  path-free native JSON profile and stored without projecting it into a second rich IR.
- Q: How is Docling's unsigned 64-bit `origin.binary_hash` retained inside I-JSON/JCS?
  → A: The export profile preserves its exact integer digits as a decimal JSON string.
  No other out-of-safe-range integer is transformed; it fails strict validation.
- Q: Is partial provider success acceptable?
  → A: No. The first profile fails closed on partial success so incomplete evidence is
  never silently advertised as complete.
- Q: How is cancellation bounded in this feature?
  → A: Parent interruption terminates the spawned worker and prevents READY commit.
  Durable queued-job cancellation belongs to F012 and is not introduced early.
- Q: How are provider pointers consumed?
  → A: They are bounded JSON references scoped to the exact provider profile and native
  artifact. Resolution traverses only the already parsed in-memory native JSON value and
  never treats pointer content as a path, URL, import, or command.

## User Scenarios & Testing

### User Story 1 - Ingest Rich Local Documents Offline (Priority: P1)

As a local user, I can ingest a PDF, DOCX, or PPTX and receive an immutable native
representation plus source-bound evidence projections without allowing the document
or parser to contact external services.

**Why this priority**: Rich local ingestion is the first independently useful
provider-backed capability and the foundation for every later context, visual, and MCP
feature.

**Independent Test**: In a fresh local workspace, ingest one reviewed synthetic document
of each supported format and verify that each successful result retains one exact native
artifact and a non-empty, contract-conformant evidence bundle while all network access is
denied.

**Acceptance Scenarios**:

1. **Given** a valid supported local document and all required local parser assets,
   **When** the user ingests it, **Then** the original bytes, complete native
   representation, descriptor, evidence records, and retrieval bodies are stored by
   content identity and committed atomically.
2. **Given** DOCX or PPTX content that needs no model bundle, **When** the user ingests it
   with the local profile, **Then** ingestion completes without network access or an
   external model service.
3. **Given** a PDF whose profile requires locally provisioned parser assets, **When**
   those reviewed assets are absent or inconsistent, **Then** ingestion fails before
   parsing with a sanitized actionable category and no network fallback.
4. **Given** document text that resembles an instruction, URL, path, or tool request,
   **When** it is projected, **Then** it remains untrusted data and causes no external
   action.

---

### User Story 2 - Reuse Exact Native Work Safely (Priority: P2)

As a local user, I can ingest the same unchanged document repeatedly without invoking
the rich parser again, while changed bytes create a separate immutable source and native
version.

**Why this priority**: Eliminating redundant parsing is the product's central practical
value, but reuse is safe only when authoritative source, recipe, native artifact, and
evidence integrity are all reverified.

**Independent Test**: Count parser invocations across an initial ingest, an unchanged
repeat, a forced reparse, and a changed-byte ingest; then tamper with one cached artifact
and prove reuse fails closed.

**Acceptance Scenarios**:

1. **Given** a complete READY rich representation for the same source bytes and exact
   provider recipe, **When** the document is ingested again, **Then** every required
   object and cross-record binding is verified and the parser is not invoked.
2. **Given** the same source under a changed provider version, provider-profile version,
   configuration, or model-bundle identity, **When** it is ingested, **Then** it uses a
   different representation identity and does not reuse incompatible work.
3. **Given** changed source bytes at the same logical path, **When** the document is
   ingested, **Then** the prior source/native version remains immutable and a new version
   becomes current only after a complete successful commit.
4. **Given** a forced reparse, **When** its provider output is byte-identical, **Then**
   content-addressed objects converge without duplicate mutable facts; when valid output
   differs, a complete append-only divergence attempt is retained and reported while the
   accepted READY representation and current head remain unchanged.

---

### User Story 3 - Fail Closed Under Parser and Storage Faults (Priority: P3)

As an operator, I receive bounded, body-free diagnostics and no partially READY evidence
when parsing times out, crashes, is cancelled, exceeds limits, encounters malformed
input, or cannot publish storage.

**Why this priority**: Rich parsers process hostile structured input and heavy resources;
failure behavior is part of the security boundary rather than optional polish.

**Independent Test**: Inject timeout, crash, cancellation, invalid output, malformed
document, output-limit, network, and storage-publication failures and verify worker
termination, sanitized failure state, source immutability, and absence of incomplete
READY records.

**Acceptance Scenarios**:

1. **Given** a worker that exceeds its deadline or resource/output limit, **When** the
   bound is reached, **Then** the worker is terminated, IPC and temporary resources are
   closed, and the representation is recorded as failed without exposing document data.
2. **Given** user cancellation or process interruption, **When** the parent stops the
   operation, **Then** the child cannot continue in the background and no partial result
   becomes current.
3. **Given** a parser crash, malformed result, partial provider success, or unsupported
   media, **When** ingestion handles the failure, **Then** it emits one stable sanitized
   category and retains no unverified projection.
4. **Given** disk exhaustion or atomic-publication failure at any output stage, **When**
   commit cannot complete, **Then** the catalog exposes no partially READY rich
   representation and a later retry remains safe.

---

### User Story 4 - Inspect and Resolve Evidence Without Provider Leakage (Priority: P4)

As an integration author, I can validate the stored bundle, enumerate bounded evidence
metadata, retrieve exact evidence bodies, and resolve reviewed opaque pointers against
the retained native artifact without depending on Docling classes in public contracts.

**Why this priority**: The adapter is independently useful only if its output can be
verified and consumed through the provider-neutral F006 boundary.

**Independent Test**: Load a stored bundle using only OpenARDP domain and storage APIs,
validate every F006 record, retrieve each referenced body by digest, and resolve valid
and invalid profile-scoped pointers without network or arbitrary filesystem access.

**Acceptance Scenarios**:

1. **Given** headings, text, tables, table cells, pictures, and page provenance in the
   native document, **When** projection completes, **Then** the evidence bundle contains
   deterministic text-span, table-cell, page-region, or profile-scoped opaque-pointer
   anchors as applicable.
2. **Given** a valid profile-scoped pointer, **When** it is resolved, **Then** the target
   is read from the exact retained native artifact and returned only as bounded
   untrusted JSON data.
3. **Given** a pointer for another profile/version, malformed syntax, missing target, or
   unsafe traversal-like value, **When** it is resolved, **Then** resolution fails
   deterministically without treating the value as a path, URI, or executable object.
4. **Given** a consumer that does not install Docling, **When** it validates stored F006
   roots and bundle metadata, **Then** validation succeeds without importing any
   provider package.

### Edge Cases

- A local file has a supported suffix but mismatched or malformed bytes.
- A source changes during snapshotting, after snapshotting, or during a failed retry.
- An OOXML archive contains traversal names, links, extreme compression, oversized
  members, excessive members, external relationships, or embedded instruction-like text.
- A PDF has zero pages, more than the configured page limit, encrypted content, malformed
  cross-references, extremely large coordinates, or requires absent model artifacts.
- Provider output contains no projectable text, duplicate or cyclic native references,
  invalid Unicode, non-finite numbers, unsafe integers, unknown item labels, or
  unsupported coordinate origins.
- Native JSON or retrieval output exceeds its individual or aggregate bound.
- Two candidates would produce the same evidence identifier but disagree semantically.
- A table cell has missing text, merged spans, negative indices, or a missing table
  pointer.
- A bounding box uses a bottom-left origin, lies partly outside page bounds, or rounds to
  zero area in fixed-point coordinates.
- A provider upgrade changes serialization or evidence ordering for unchanged source
  bytes.
- A cached object exists but its length, digest, record identity, source binding, recipe,
  or catalog projection is inconsistent.
- The configured model bundle contains symlinks, missing files, digest drift, duplicate
  paths, an unreviewed license entry, or a path outside its declared root.
- Cancellation occurs while input is being streamed, while output is being returned, or
  while CAS publication is in progress.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST support local PDF, DOCX, and PPTX source bytes through one
  narrow provider-neutral rich-parser port and one Docling provider profile.
- **FR-002**: Rich-parser support MUST be optional for the installed core package, while
  an explicitly selected installation MUST pin and lock an exact compatible Docling
  release and its transitive dependency graph.
- **FR-003**: The dependency and model supply chain MUST document maintenance, license,
  provenance, platform, Python, model-license, and offline-asset constraints.
- **FR-004**: The default rich profile MUST disable OCR, captioning, remote services,
  automatic model download, and every unreviewed enrichment; PDF parsing MUST require
  a validated local model bundle when the selected pipeline needs one.
- **FR-005**: The parser MUST receive verified source bytes through a bounded stream and
  a synthetic media-derived name, never source-path authority, a URL, credentials, or
  arbitrary headers.
- **FR-006**: Parser execution MUST occur in a spawned killable worker with explicit
  source-byte, page, elapsed-time, CPU, memory where portable, file-descriptor, native
  output, projection-count, per-body, and aggregate-body limits.
- **FR-007**: The worker MUST deny socket creation before provider import and MUST enable
  documented offline modes; the boundary MUST be described as bounded
  defense-in-depth, not a universally strong sandbox.
- **FR-008**: Successful parsing MUST serialize the complete provider-native document
  representation through one documented, versioned, path-free native export profile
  without converting it into a complete OpenARDP-owned rich model. The profile MUST
  losslessly encode Docling's unsigned 64-bit `origin.binary_hash` as a decimal string
  when it exceeds the I-JSON safe-integer range and MUST reject every other unsafe
  number rather than round or omit it.
- **FR-009**: The adapter descriptor MUST record provider name and exact version,
  provider-profile name and independent version, configuration digest, native media
  type, source identity, native artifact identity and length, creation time, relevant
  component versions, local model-bundle identity when applicable, and observed
  nondeterminism limitations.
- **FR-010**: The provider recipe and representation identity MUST change when source
  bytes, provider version, provider-profile version, native export profile,
  projection configuration, limit-affecting semantics, or model-bundle identity changes.
- **FR-011**: Every successful result MUST emit one F006 `NativeRepresentation`, one or
  more F006 `EvidenceReference` records, and corresponding thin F006
  `EvidenceProjection` records unless the reviewed source contains no projectable
  evidence, in which case the READY native-only outcome MUST report zero evidence and
  MUST NOT fabricate or advertise a retrieval projection.
- **FR-012**: Evidence projection MUST cover text and headings, tables and table cells,
  pictures or page regions, and opaque native pointers when those elements exist,
  without embedding a complete provider tree or provider runtime type.
- **FR-013**: Text offsets MUST use one documented deterministic provider-profile text
  view; page geometry MUST be converted safely to F006 fixed-point top-left coordinates;
  table coordinates and spans MUST be validated before construction.
- **FR-014**: Provider pointers MUST be opaque, bounded, profile/version scoped,
  path-independent, and resolvable only inside the exact retained native JSON object.
- **FR-015**: Retrieval bodies MUST be immutable content-addressed UTF-8 or JSON values
  with explicit media type and length, and each returned body MUST be digest-verified.
- **FR-016**: All native, reference, projection, retrieval, and bundle records MUST pass
  local identity, structural, source/native binding, trust anti-escalation, and aggregate
  validation before becoming READY.
- **FR-017**: Document-originated and provider-derived content MUST remain role `data`,
  instruction execution false, and no more trusted than its declared source origin.
- **FR-018**: Rich output MUST be committed atomically with catalog reachability for the
  descriptor, complete native artifact, evidence bundle, projection records, and
  retrieval objects; partial publication MUST never create a READY aggregate.
- **FR-019**: The catalog evolution MUST be transactional, checksummed,
  backward-compatible with existing workspaces, restart-safe, and reject newer or
  drifted schemas without mutation.
- **FR-020**: A repeated ingest of unchanged source bytes under the exact same recipe
  MUST verify every required authoritative object and reuse it without invoking Docling.
- **FR-021**: Changed source bytes or recipe identity MUST create a separate immutable
  representation; prior versions and native artifacts MUST remain unmodified.
- **FR-022**: Forced reparse MUST be explicit, MUST NOT rewrite an existing
  content-addressed object, and MUST report whether native bytes converged or differed.
  A differing valid output MUST be retained as a complete append-only parse attempt with
  its own artifacts/evidence while the accepted READY representation and current head
  remain unchanged.
- **FR-023**: Timeout, crash, cancellation, malformed/partial provider output,
  unsupported media, network attempt, resource excess, and storage failure MUST map to
  stable body-free categories and fail closed.
- **FR-024**: Cancellation and every failure path MUST terminate the child, close IPC,
  avoid background work, preserve originals, and leave no incomplete READY state.
- **FR-025**: Logs, CLI envelopes, failure records, and diagnostics MUST omit document
  bodies, native payloads, query text, credentials, and absolute source/model paths by
  default.
- **FR-026**: The CLI MUST retain existing text-ingest behavior, route supported rich
  media explicitly, expose required local-model configuration without accepting URLs,
  and return bounded deterministic JSON plus useful human-readable outcomes.
- **FR-027**: Provider-specific pointer resolution and bundle inspection MUST operate
  without network, arbitrary filesystem reach, executable deserialization, or public
  Docling types.
- **FR-028**: Unit tests MUST use synthetic or redistributable fixtures and no network;
  cross-platform CI MUST exercise dependency installation, worker lifecycle, rich
  ingestion semantics, cache reuse, failures, and packaging on Linux, macOS, and Windows.
- **FR-029**: At least one actual provider smoke path for DOCX and PPTX MUST run in the
  locked test environment; PDF provider execution MUST run when reviewed local model
  assets are available and otherwise have a deterministic, tested fail-closed path.
- **FR-030**: Existing text ingestion, lexical search, five earlier public schemas, four
  F006 schemas, evidence conformance corpus, identity vectors, and default no-network
  behavior MUST remain compatible and pass unchanged.
- **FR-031**: No network access may occur in tests, provider runtime defaults, cache
  validation, pointer resolution, or CLI operation.
- **FR-032**: Public documentation, CLI help, installation guidance, changelog,
  implementation notes, migration evidence, operational limits, rollback, and
  nondeterminism caveats MUST match delivered behavior.
- **FR-033**: Public functions and provider boundaries MUST be typed and documented; no
  public contract may leak Python, SQLite, local path, or Docling runtime objects.

### Non-Goals and Compatibility Impact

- **Non-goal**: OCR, picture captioning, remote models, cloud parsing, semantic search,
  context compilation, MCP, watchers, durable cancellation jobs, visual rendering,
  reconciliation, exports, or an alternate parser.
- **Non-goal**: A second complete rich-document IR, cross-provider pointer equivalence,
  arbitrary native-object querying, or bidirectional Office/PDF editing.
- **Non-goal**: Automatic download, redistribution, or licensing approval of model
  weights.
- **Compatibility impact**: Additive application and provider-profile capability with a
  transactional workspace migration. The F006 evidence contract stays at experimental
  `0.1.0` with unchanged schema and identity semantics. Application version may advance;
  export-profile versions are unaffected.

### Key Entities

- **Rich Parser Recipe**: Exact provider, profile, export/projection policy, limit
  semantics, and optional local model-bundle identity that determine compatible reuse.
- **Native Artifact Descriptor**: Reproducibility and provenance facts for one complete
  retained Docling-native JSON artifact.
- **Rich Parse Output**: Bounded worker result containing complete native bytes,
  projection candidates, warnings, and sanitized provider metadata before persistence.
- **Evidence Candidate**: Provider-profile-scoped source item with one reviewed anchor,
  bounded retrieval body, ordinal, optional parent, and trust origin.
- **Rich Evidence Bundle**: Internal immutable aggregate containing the F006 native
  record, references, projections, descriptor, and exact record-object inventory.
- **Model Bundle Manifest**: Optional local, path-confined inventory of PDF model files,
  digests, lengths, versions, and reviewed licenses whose identity enters the recipe.
- **Rich Catalog Projection**: Body-free catalog rows connecting a representation scope
  to descriptor, native, bundle, reference/projection, and retrieval objects.
- **Rich Parse Attempt**: Append-only canonical/converged/diverged execution record that
  keeps every valid forced-reparse artifact reachable without mutating the accepted
  READY representation.

## Success Criteria

### Measurable Outcomes

- **SC-001**: One command successfully ingests each reviewed synthetic DOCX and PPTX
  fixture in a clean locked environment with zero network calls and produces a verified
  native artifact plus at least one evidence projection.
- **SC-002**: A reviewed PDF fixture either completes with a validated local model bundle
  or fails before provider execution with the documented missing/inconsistent-assets
  category; it never attempts a download.
- **SC-003**: Across ten unchanged repeat ingests, parser invocation count remains zero
  after the initial commit and every repeat revalidates all authoritative objects.
- **SC-004**: Changed bytes or any identity-significant recipe change produces a distinct
  representation in 100% of reviewed cases while all prior source/native objects remain
  byte-identical.
- **SC-005**: Every projected record in the reviewed corpus passes F006 model and
  aggregate validation, and 100% of retrieval bodies and native artifacts pass digest and
  length verification before return.
- **SC-006**: Timeout, crash, cancellation, network, malformed input, invalid output,
  output excess, and storage-publication fault tests create zero incomplete READY
  aggregates and terminate the spawned worker within five seconds of parent handling.
- **SC-007**: The full locked gate, including actual DOCX/PPTX provider smoke tests,
  passes on Linux, macOS, and Windows with no tracked-file drift and at least 85% branch
  coverage.
- **SC-008**: Core installation and all F006 contract validation remain usable without
  importing or installing Docling; selecting rich ingestion without the extra returns
  one stable actionable dependency category.
- **SC-009**: The five pre-F006 schemas, four F006 schemas, established identity vectors,
  and all prior tests remain unchanged in semantics and pass in the complete suite.
- **SC-010**: No reviewed log, CLI error, catalog failure record, or default diagnostic
  contains a document body, native payload, credential, or absolute source/model path.
- **SC-011**: The final implementation records exact provider/dependency versions,
  license and provenance review, local and cross-platform commands, known
  nondeterminism, resource defaults, residual risks, and one-command rollback guidance.
- **SC-012**: In every injected valid nondeterministic reparse case, all differing
  artifacts remain digest-verifiable through one append-only divergence attempt while
  the previously accepted READY representation and current head remain byte-for-byte
  and semantically unchanged.

## Assumptions

- OpenARDP remains a local, single-user, single-workspace application.
- Rich parser support is an explicitly installed optional capability; the core package
  remains lightweight and provider-neutral.
- Docling `2.114.0` is the reviewed initial provider version, subject to exact lockfile
  resolution and three-platform verification before implementation is accepted.
- The initial provider profile disables OCR, captioning, remote services, automatic
  model downloads, and unreviewed enrichments.
- DOCX and PPTX use model-free local backends. PDF layout parsing requires a separately
  provisioned, license-reviewed local model bundle whose files are never redistributed
  by this feature.
- Partial provider success is treated as failure in the first profile because incomplete
  native evidence cannot be silently presented as complete.
- Existing source snapshot, content-addressed store, representation lease, catalog head,
  and append-only ingest-event mechanisms are extended rather than replaced.
- Worker resource controls are portable best-effort defense-in-depth; operating-system
  guarantees differ and are reported honestly.
- Parser performance varies materially by document and hardware. F007 measures
  invocation/reuse and bounded termination but makes no universal throughput claim.
