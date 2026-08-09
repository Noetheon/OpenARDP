# Feature Specification: Text Ingestion Vertical Slice

**Feature Branch**: `codex/f004-text-ingestion-slice`

**Created**: 2026-07-22

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: User description: "Implement every remaining feature completely, one after another, with one complete commit per feature and with long-term, sustainable best practices. For F004, deliver the bounded TXT/Markdown ingestion vertical slice from the feature map."

## Clarifications

### Session 2026-07-22

- Q: How is a workspace selected after `init`? → A: Every command accepts an explicit `--store PATH`; when omitted it
  uses `.openardp` below the current directory. Commands never search parent directories or silently adopt another store.
- Q: What identifies a local source and which path forms are accepted? → A: The connector is `local`; its locator is the
  absolute canonical path captured after rejecting symlink components, control characters and non-regular leaves. An
  explicitly named regular file may be outside the workspace because the CLI invocation itself grants that one read.
- Q: What does the built-in Markdown adapter promise? → A: It preserves the exact decoded UTF-8 parser-native text and
  deterministically recognizes ATX/setext headings, paragraphs, fenced code, block quotes and list items. Inline rendering,
  HTML interpretation, tables and CommonMark-conformance claims are excluded.
- Q: What happens for an empty or whitespace-only source? → A: It is a valid immutable source and ready representation
  with zero content blocks, an empty outline and a manifest/native artifact; this is distinct from failed ingestion.
- Q: How does `--force` interact with unchanged reuse? → A: Ordinary unchanged ingest MUST skip parsing. Explicit
  `--force` re-runs and revalidates the same deterministic recipe, then converges idempotently on the existing immutable
  representation or raises a conflict if output differs; it does not create a synthetic source or recipe revision.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Initialize and inspect a local workspace (Priority: P1)

As a local operator, I can initialize one explicit OpenARDP workspace and inspect its state through stable human-readable
or JSON CLI output, so every later ingest targets a known local catalog and object store without hidden cloud behavior.

**Why this priority**: The command surface must establish a deterministic, private local boundary before source content is
accepted or queried.

**Independent Test**: Initialize a temporary workspace twice, invoke `list` and `status`, and verify the expected layout,
schema revision, idempotency, machine-readable envelopes and absence of network or source-content side effects.

**Acceptance Scenarios**:

1. **Given** an unused local directory, **When** the operator initializes it, **Then** the managed CAS and current SQLite
   catalog are created with restrictive best-effort permissions and a versioned workspace marker.
2. **Given** an already valid compatible workspace, **When** initialization is repeated, **Then** it succeeds idempotently
   without changing committed document data.
3. **Given** a missing, foreign, malformed or newer workspace, **When** a read or ingest command targets it, **Then** the
   command fails with a stable classification and does not initialize, repair or partially mutate it implicitly.
4. **Given** any supported command, **When** `--json` is selected, **Then** exactly one versioned JSON result or error
   envelope is written to standard output and document body content is not included unless `get` explicitly requests it.

---

### User Story 2 - Ingest source-backed TXT and Markdown once (Priority: P1)

As a local operator, I can ingest a UTF-8 TXT or Markdown file into a validated immutable representation, so its outline
and exact normalized blocks can be reused without modifying or repeatedly parsing the original.

**Why this priority**: This is the first end-to-end proof of the project's "parse once, reuse many" promise.

**Independent Test**: Ingest synthetic TXT and Markdown fixtures through the application service and CLI, then verify the
source bytes, manifest, parser-native artifact, normalized blocks, hierarchy, provenance and query results independently
from the original path.

**Acceptance Scenarios**:

1. **Given** a regular UTF-8 TXT file, **When** it is ingested, **Then** one source version and one complete ready
   representation are committed with ordered paragraph blocks and exact line provenance.
2. **Given** a regular UTF-8 Markdown file, **When** it is ingested, **Then** headings establish a deterministic hierarchy,
   source-backed content blocks preserve exact decoded content semantics, and every block reports exact line provenance.
3. **Given** a successful ingest, **When** the original path is removed or its content later changes, **Then** `outline` and
   `get` for the committed representation still read only verified persisted artifacts and never substitute new path bytes.
4. **Given** instruction-like document text, **When** it is parsed, stored or returned, **Then** it remains untrusted data
   with instruction execution disabled and never initiates a tool, shell, network or filesystem side effect.
5. **Given** an injected failure before the representation commit, **When** independent readers inspect the workspace,
   **Then** no partial manifest, block set or ready representation is visible; any complete orphaned CAS object remains
   safe for later reachability review.

---

### User Story 3 - Reuse unchanged work and version changed sources (Priority: P1)

As a local operator, I can ingest the same source repeatedly and receive an auditable cache decision, so unchanged content
invokes no parser while changed bytes create a new immutable version under the same logical document.

**Why this priority**: Avoiding redundant parsing is the core efficiency and sustainability outcome of F004.

**Independent Test**: Instrument a parser adapter, ingest identical bytes repeatedly and then changed bytes at the same
source key, and prove exact invocation counts, stable identities, immutable history and deterministic current-version
selection.

**Acceptance Scenarios**:

1. **Given** the same source bytes and processing recipe were already committed successfully, **When** ingest is repeated,
   **Then** the prior representation is returned as a cache hit and parser invocation count remains unchanged.
2. **Given** the same bytes were committed for the source but only under a different processing recipe, **When** ingest is
   requested, **Then** the source object/version is reused but one representation for the requested recipe is produced.
3. **Given** source bytes changed at the same canonical source location, **When** ingest succeeds, **Then** a new immutable
   source version and representation become current while prior versions remain queryable.
4. **Given** a failed or incomplete prior representation, **When** ingest is retried, **Then** it is not reported as a cache
   hit and only one complete ready result can become visible.
5. **Given** concurrent ingest requests for the same source and recipe, **When** they settle, **Then** they converge on one
   committed representation or a retryable busy outcome without duplicate or partial normalized records.

---

### User Story 4 - Navigate documents without search infrastructure (Priority: P2)

As a local operator, I can list ingested documents, inspect freshness/status, view an outline and retrieve one exact block,
so I can use prepared evidence before lexical search is introduced.

**Why this priority**: The vertical slice must be independently demonstrable without leaking F005 search behavior into
this feature.

**Independent Test**: Query a workspace containing multiple document versions and recipes using `list`, `status`,
`outline` and `get`, and compare both human and JSON responses to committed catalog facts and CAS bytes.

**Acceptance Scenarios**:

1. **Given** multiple documents, **When** `list` runs, **Then** results are deterministic and include document identity,
   source locator, current source version, representation state and last ingestion time without document bodies.
2. **Given** a registered path or document identifier, **When** `status` runs, **Then** it distinguishes missing, registered
   without a ready representation, current, source-changed and source-missing states without parsing the file.
3. **Given** a ready representation, **When** `outline` runs, **Then** it returns ordered hierarchical handles and headings
   without returning unrelated full paragraph bodies.
4. **Given** a block identifier scoped to a ready representation, **When** `get` runs, **Then** it returns that exact
   normalized source content, trust boundary and provenance; unknown or ambiguous identifiers fail explicitly.
5. **Given** a version selector, **When** `status`, `outline` or `get` requests historical data, **Then** it never silently
   mixes blocks from another source version or representation.

### Edge Cases

- An empty file, a file containing only whitespace, no trailing newline, CRLF line endings, UTF-8 BOM, non-ASCII text or
  Unicode code-point-distinct text.
- A Markdown document with skipped heading levels, repeated headings, paragraphs before the first heading, fenced code,
  block quotes, lists, thematic breaks, setext headings and delimiter-like text inside code fences.
- An unsupported extension, extension/content disagreement, invalid UTF-8, NUL bytes, an oversized source, directory,
  FIFO/device/socket, symlink or path containing control characters.
- A file changes, is replaced or is truncated while being snapshotted; metadata changes without byte changes.
- Two source locators point to byte-identical content; one locator later changes and then changes back.
- The same source/version has multiple processing profiles or a parser/config version changes.
- A catalog contains missing/corrupt representation artifacts, duplicate block identifiers, invalid parent links, cycles,
  non-contiguous sibling order or a manifest whose identities disagree with the requested representation.
- JSON output encounters document text resembling terminal escapes, log directives or commands.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST initialize an explicit local workspace containing a compatible catalog, immutable object
  store and versioned marker, and repeated initialization of that workspace MUST be idempotent.
- **FR-002**: Every command other than `init` MUST validate the workspace marker and catalog compatibility before use and
  MUST NOT silently initialize, upgrade an unrecognized workspace or access a network service.
- **FR-003**: F004 MUST expose `init`, `ingest`, `list`, `status`, `outline` and `get` through an installable `openardp`
  console command, with deterministic exit classifications and a stable versioned `--json` envelope.
- **FR-004**: Source input MUST be limited to explicitly selected regular local TXT or Markdown files within documented
  byte limits; directories, special files, symbolic links, unsupported media and unsafe paths MUST be rejected before
  parser invocation.
- **FR-005**: Ingestion MUST stream an exact snapshot into the immutable object store, derive the source version from those
  bytes, and parse only the persisted verified snapshot rather than rereading mutable source-path content.
- **FR-006**: The system MUST NOT write to, rename, normalize or otherwise alter the original source path; success, cache
  hit and every tested failure path MUST preserve its bytes, size, modification time and mode. Access time is excluded
  because a read may update it under the host filesystem policy.
- **FR-007**: The text parser port MUST be provider-neutral and the default built-in adapter MUST execute deterministic
  UTF-8 TXT/Markdown processing in a killable spawned worker with bounded input, line, block and wall-clock limits, no
  source-path capability, no network access, no model call and no later rich-document parser dependency.
- **FR-008**: The built-in adapter MUST reject malformed UTF-8, NUL bytes and inputs beyond the configured bound with
  sanitized errors that do not contain document bodies.
- **FR-009**: TXT normalization MUST produce deterministic ordered source-backed paragraph blocks; Markdown normalization
  MUST additionally represent heading hierarchy and supported core block forms without inventing content.
- **FR-010**: Every normalized block MUST satisfy the F002 `ContentBlock` contract and pin the exact document, source
  version, representation recipe, trust classification and sufficient exact source-line provenance.
- **FR-011**: Every ready representation MUST include a validated F002 `DocumentManifest`, parser-native lossless artifact,
  complete ordered block sequence and explicit parent/order relationships.
- **FR-012**: Representation identity MUST use the accepted RFC 8785 recipe projection and MUST change exactly when its
  source version, parser identity/profile/configuration or normalization schema version changes.
- **FR-013**: The catalog MUST persist representation state, immutable recipe facts, manifest/native/block object
  references and normalized block metadata through one ordered checksummed migration.
- **FR-014**: A representation MUST become visible as ready only when its manifest, native artifact, complete block set,
  hierarchy and object references validate and commit atomically; failures MUST expose no partial ready representation.
- **FR-015**: A committed ready representation MUST be immutable and an equivalent retry MUST be idempotent; conflicting
  reuse of a representation or block identity MUST fail without modifying existing state.
- **FR-016**: Before parser invocation, ingestion MUST check for a complete ready representation matching the exact source
  version and processing recipe; an unchanged match MUST return an auditable cache hit and invoke the parser zero times.
- **FR-017**: Cache eligibility MUST require verified referenced objects and complete representation records; missing,
  corrupt, failed or staging data MUST never be reported as a reusable hit.
- **FR-018**: A changed source at the same canonical source key MUST create a new immutable source version while retaining
  the logical document identifier and all earlier committed versions.
- **FR-019**: Concurrent equivalent ingestion MUST serialize or converge at the source/recipe boundary so at most one
  complete representation is committed and no reader observes partial state.
- **FR-020**: `list` MUST return a deterministic document summary without bodies; `status` MUST distinguish current,
  changed, missing and incomplete source/representation states without invoking the parser.
- **FR-021**: `outline` MUST return a deterministic hierarchy with block handles and bounded labels; `get` MUST return one
  exact block only when its complete representation/version scope is unambiguous and ready.
- **FR-022**: Read commands MUST obtain normalized records from verified persisted artifacts and MUST never fall back to
  current bytes at the original path.
- **FR-023**: Source text MUST remain `role=data` with `instruction_execution_allowed=false`; document content MUST never
  be interpreted as commands, configuration, paths, URLs or tool instructions.
- **FR-024**: Default logs, diagnostics and errors MUST contain bounded identifiers/classifications and timings only, not
  source body content, raw parser payloads or untrusted exception text.
- **FR-025**: Every public parser, ingestion, catalog and CLI contract plus each persisted behavior and security boundary
  introduced by F004 MUST have deterministic synthetic offline tests.
- **FR-026**: F004 MUST remain bounded to TXT/Markdown ingestion and navigation; FTS/search, PDF/DOCX/PPTX, Docling,
  embeddings, enrichment, reconciliation/reuse across changed versions, watchers, MCP, HTTP and package export are out of
  scope.

### Key Entities

- **Workspace**: Explicit local state root with versioned marker, SQLite catalog and filesystem CAS; it is not a source
  directory or an implicit cloud account.
- **Parser Recipe**: Immutable parser name, version, profile, configuration identity and normalization schema version used
  to derive one representation identity.
- **Parsed Text Document**: Deterministic adapter result derived from the lossless source snapshot and containing normalized
  candidate blocks, hierarchy and bounded warnings before document-specific identities are assigned. The exact source CAS
  object remains the lossless native artifact rather than being duplicated into the result envelope.
- **Document Representation**: Immutable complete processing result for one logical document, source version and parser
  recipe, with lifecycle state and object references.
- **Normalized Block Record**: Catalog projection and serialized F002 block pinned to one exact representation and source
  line range.
- **Ingestion Result**: Bounded application outcome identifying document, source version, representation, cache decision,
  state, block count and warnings without embedding document body text.
- **Document Status**: Read-only freshness comparison between a registered source path, committed current version and
  complete representation; it never authorizes parsing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For both a synthetic TXT and Markdown fixture, first ingest creates one ready representation whose manifest,
  native artifact and every block can be independently loaded and validated from the CAS after the source path is removed.
- **SC-002**: Across at least 20 repeated unchanged ingests and at least 8 concurrent unchanged requests, parser invocation
  count remains exactly one and every successful result identifies the same representation.
- **SC-003**: After a one-byte source change at the same source key, the next successful ingest creates exactly one new
  version/representation while the old version and its blocks remain byte-for-byte queryable.
- **SC-004**: Fault injection at every representation publication/commit boundary yields zero partially visible ready
  representations and no change to the original source.
- **SC-005**: Every returned block validates against the F002 model, pins the selected document/version/representation and
  reports exact one-based line boundaries that reproduce its normalized text from the persisted native artifact.
- **SC-006**: The negative corpus for invalid UTF-8, NUL, unsupported media, oversized files, links, special files, path
  replacement and malicious instruction-like text causes zero parser-triggered side effects, zero network calls and zero
  source writes.
- **SC-007**: Human and JSON forms of all six CLI commands have deterministic integration tests; JSON responses validate
  the documented envelope and no non-`get` success response includes full block body text.
- **SC-008**: The full locked repository gates pass offline on Python 3.12 and the complete suite passes on Linux, macOS
  and Windows CI.

## Assumptions

- The workspace is an operator-selected, app-owned state directory; source files are separate and are accepted only by an
  explicit `ingest` invocation in F004.
- The built-in text adapter is intentionally narrow. It preserves decoded UTF-8 text and recognizes a reviewed subset of
  Markdown structure; it does not claim CommonMark conformance or rich-document fidelity.
- Line-based source provenance is sufficient for TXT/Markdown. Page, slide and bounding-box coordinates remain null.
- F004 may declare a representation ready without an FTS index because F005 is not installed and therefore no index is a
  required artifact for this feature's processing profile.
- Original-file metadata is advisory for status display; exact bytes and SHA-256 determine source-version identity and
  unchanged-ingest reuse.
- Cross-process work is coordinated through the local catalog and bounded SQLite locking; shared/network filesystems and
  actively malicious same-user processes remain outside the supported persistence boundary.

## Dependencies

- Converged F001 repository, packaging and three-platform quality gates.
- Converged F002 models, schemas and RFC 8785 identity helpers.
- Converged F003 immutable CAS, transactional SQLite catalog, source-version persistence and reachability behavior.
- OpenARDP constitution, `AGENTS.md`, accepted ADRs 0002 and 0006, and the architecture/security/test documents.

## Out of Scope

- SQLite FTS5, lexical or semantic search and ranking.
- PDF, DOCX, PPTX, images, archives, Docling, MarkItDown or MinerU dependencies.
- Block reconciliation or derived-artifact reuse across changed source versions.
- OCR, summaries, captions, embeddings, model/provider calls and external fetching.
- Watchers, background daemons, job-worker scheduling and automatic retries.
- MCP, HTTP, cloud connectors, permissions, multi-tenant behavior and telemetry backends.
- Portable `.ardp.zip` export/import, retention, garbage deletion and source editing.
