# Feature Specification: Lexical Search over Prepared Evidence

**Feature Branch**: `codex/f005-lexical-search`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Implement every remaining feature completely, one after another, with one complete commit
per feature and with long-term, sustainable best practices. For F005, deliver work package 4 from the feature map:
exact source-backed retrieval through SQLite FTS5 with block indexing, filters and a `search` command."

## Clarifications

### Session 2026-07-22

- Q: How does the explicit backfill surface to operators? → A: Through one dedicated CLI verb (`reindex`) rather than
  hidden writes inside read commands; automatic indexing on workspace open was rejected because durable writes must be
  explicit and auditable (Constitution Article V). Exact argument shape is decided in planning.
- Q: Which document scopes does the filter accept? → A: The `--document` filter accepts a document UUID or an exact
  source path, resolved with the same deterministic precedence as the F004 `status` target; unknown scopes fail with
  the stable not-found classification.
- Q: Is the raw FTS5 `MATCH` operator language exposed? → A: No. The query grammar is bounded to terms and quoted
  phrases; operator-like tokens (AND/OR/NEAR/wildcards/column selectors) are treated as literal text and validated
  input, because queries are untrusted operator input (Constitution Article IV).
- Q: What are the result-limit bounds? → A: Default 20 hits, accepted range 1–100; truncation beyond the limit is
  reported explicitly (Constitution Article VI progressive delivery).
- Q: Which values do the trust and kind filters use? → A: The trust filter uses the F002 `TrustZone` vocabulary
  (`local_trusted`, `organization_trusted`, `external_untrusted`) and the kind filter uses the F002 `BlockKind`
  vocabulary; both are validated against the stable enumerations with a rejected-input classification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index prepared documents automatically and verifiably (Priority: P1)

As a local operator, I can rely on every successfully prepared document becoming searchable as part of its atomic
preparation, and on documents prepared before this feature becoming searchable through one explicit deterministic
backfill, so search never silently omits committed evidence or requires undocumented manual steps.

**Why this priority**: Search results are only trustworthy when index coverage is complete, atomic with the evidence
commit and provably derived from verified persisted records rather than from mutable sources.

**Independent Test**: Prepare synthetic documents before and after the index capability exists, run the documented
backfill once, then compare index coverage against committed catalog facts for every current ready representation
without any original source file being present.

**Acceptance Scenarios**:

1. **Given** a successful ingest of a changed or new source, **When** the ready representation commits, **Then** its
   searchable index entries become visible in the same atomic operation and never before the representation is ready.
2. **Given** an injected failure during index population, **When** independent readers inspect the workspace, **Then**
   no partial ready representation is exposed and the incomplete index state is either absent or detected and excluded
   until a verified rebuild completes.
3. **Given** a workspace whose representations were committed before index support, **When** the documented backfill
   runs, **Then** it reads only verified persisted artifacts, completes idempotently and reports a bounded per-scope
   outcome without altering representations, source versions or original files.
4. **Given** an index whose rows drift from catalog projections (missing, orphaned or stale entries), **When** coverage
   is inspected, **Then** the drift is detected deterministically, affected results are never silently served from
   unverifiable rows, and a rebuild restores consistency from verified evidence.

---

### User Story 2 - Find exact text with source-backed evidence (Priority: P1)

As a local operator, I can search one exact term or phrase across my prepared documents and receive a deterministic
bounded result list where every hit identifies its exact document, source version, block handle, provenance and a
bounded snippet, so I can decide what to retrieve in full without loading document bodies.

**Why this priority**: Exact source-backed retrieval is the core user value of work package 4 and the first retrieval
surface of the product.

**Independent Test**: Ingest synthetic TXT and Markdown fixtures with known term placement, run term and phrase
searches through the application service and CLI, and compare every returned reference and snippet against committed
catalog facts and verified persisted block content.

**Acceptance Scenarios**:

1. **Given** documents containing a known term in several blocks, **When** the operator searches that term, **Then**
   every matching current block appears exactly once with its exact document, version, representation, block handle,
   line provenance and a bounded highlighted snippet.
2. **Given** documents containing a known multi-word phrase, **When** the operator searches the quoted phrase,
   **Then** only blocks containing the exact adjacent phrase match; blocks containing the words separately do not.
3. **Given** a fixed corpus, **When** the same query repeats, **Then** the hit set, ranking order and snippets are
   identical, and ties resolve through a documented total order rather than storage or insertion order.
4. **Given** a query with no matches, an empty query or only whitespace, **When** search runs, **Then** the outcome is
   an explicit empty or rejected-input classification, never an error containing document body content.
5. **Given** instruction-like document text inside matched blocks, **When** results render in human or JSON form,
   **Then** the text remains inert data with instruction execution disabled and no tool, shell, network or filesystem
   side effect occurs.

---

### User Story 3 - Scope and filter retrieval deterministically (Priority: P2)

As a local operator, I can restrict search by document, source version, block kind, trust classification and result
limit, and optionally include historical ready versions, so I can narrow evidence precisely while superseded versions
stay excluded by default.

**Why this priority**: Scoped retrieval makes the evidence boundary explicit and prepares the filter surface that
richer document formats will reuse, without weakening the safe current-only default.

**Independent Test**: Prepare multiple documents with multiple versions and block kinds, then verify every filter
combination and the historical opt-in against committed catalog facts in both human and JSON modes.

**Acceptance Scenarios**:

1. **Given** a document with a superseded and a current version both containing a term, **When** the operator searches
   without history options, **Then** only current-version blocks match; with the explicit history option, the superseded
   version's blocks appear with their exact version identity.
2. **Given** documents with headings, paragraphs, list items, code and quotes, **When** the operator filters by one
   block kind, **Then** only blocks of that kind match and the kind is validated against a stable classification.
3. **Given** several documents containing the same term, **When** the operator scopes by one document identifier or
   exact source version, **Then** only blocks inside that scope match and unknown scopes fail with a stable
   not-found classification.
4. **Given** more matching blocks than the selected limit, **When** search runs, **Then** the result is truncated
   deterministically in ranking order and reports that truncation, and the limit is validated against documented
   bounds.
5. **Given** a page or slide filter against line-based text representations, **When** search runs, **Then** the filter
   is accepted as part of the stable contract and matches only blocks that carry that exact coordinate, which current
   text blocks never do; the behavior is documented rather than silently broadened.

---

### User Story 4 - Operate search through the stable CLI boundary (Priority: P2)

As a local operator or automation author, I can use `search` through the installable `openardp` command with the same
workspace validation, human/JSON envelope and exit classification as the existing commands, so retrieval composes
safely with `init`, `ingest`, `list`, `status`, `outline` and `get`.

**Why this priority**: Search must extend the audited CLI contract instead of introducing a divergent interface.

**Independent Test**: Exercise `search` in human and JSON mode against valid, missing, foreign and newer workspaces and
against rejected input, comparing envelopes, exit codes and body-minimizing output with the documented contract.

**Acceptance Scenarios**:

1. **Given** a valid workspace, **When** `search --json` runs, **Then** exactly one versioned JSON envelope is written
   and each hit carries identifiers, provenance, trust classification, rank and a bounded snippet, while full block
   bodies remain available only through `get`.
2. **Given** a missing, foreign, malformed or newer workspace, **When** `search` runs, **Then** it fails with the
   shared workspace classification and does not initialize, repair or partially mutate the workspace implicitly.
3. **Given** a malformed or unsupported query or filter value, **When** `search` runs, **Then** it fails with a
   rejected-input classification whose message is bounded and free of document body content.
4. **Given** an index capability that the current runtime cannot provide, **When** any index-dependent command runs,
   **Then** it fails with a sanitized integrity/capability classification before serving any result.

### Edge Cases

- Queries containing punctuation, operator-like tokens, quotes, wildcards, Unicode, mixed case, very long terms or
  only stop-word-like tokens.
- Documents whose normalized text contains query syntax lookalikes, terminal escape lookalikes or log directives.
- A block whose text matches multiple query terms or contains many adjacent phrase repetitions.
- Empty documents, documents with only whitespace blocks and documents whose only matches live in superseded versions.
- Concurrent ingest and search against the same workspace, including a representation becoming current mid-query.
- An index built for one representation recipe queried after the source changes and after a forced reparse.
- Pre-feature workspaces migrated forward, newer workspaces, and catalogs with missing or corrupt block artifacts.
- Result limits at, below and beyond documented bounds; snippet bounds around very long lines and Unicode boundaries.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: F005 MUST extend the existing workspace with one ordered checksummed catalog migration that adds the
  mandated local FTS5 block index; foreign, gapped, drifted or newer histories MUST fail closed without mutation.
- **FR-002**: Index rows for a representation MUST become visible only inside the same atomic commit that makes the
  representation ready; a failed index population MUST roll back the entire ready commit and expose no partial state.
- **FR-003**: Indexed text MUST be derived from verified persisted normalized block records whose identities match their
  catalog projections; the original source path MUST never be read for indexing or searching.
- **FR-004**: Representations committed before index support MUST become searchable through the explicit deterministic
  `reindex` command, which verifies each referenced artifact, is idempotent, reports bounded per-scope outcomes and
  leaves all existing evidence byte-for-byte unchanged.
- **FR-005**: Index coverage MUST be deterministically verifiable against catalog projections; missing, orphaned or
  stale rows MUST be detected, MUST never be served as evidence and MUST be repairable by a verified rebuild only.
- **FR-006**: Search MUST support exact term queries and exact quoted-phrase queries through a bounded documented query
  grammar in which operator-like tokens (AND/OR/NEAR, wildcards, column selectors) are literal text; malformed queries
  MUST be rejected with a sanitized classification and query text MUST be treated as untrusted input, never
  interpolated into SQL.
- **FR-007**: Result ranking MUST be deterministic for a fixed corpus: relevance scores from the index MUST be combined
  with a documented total tie-break order so repeated identical queries return identical ordered results.
- **FR-008**: Every hit MUST identify its exact document, source version, representation, block handle, block kind,
  trust classification and exact source-line provenance, plus a bounded snippet; full bodies MUST require an explicit
  `get`.
- **FR-009**: Default search scope MUST include only blocks of the current ready head representation of each document;
  superseded or non-ready versions MUST be excluded unless the operator explicitly opts into history.
- **FR-010**: Search MUST support filters for document identity (UUID or exact source path, resolved like the F004
  `status` target), exact source version, block kind (F002 `BlockKind` vocabulary), trust classification (F002
  `TrustZone` vocabulary) and a documented result limit; unknown scopes and invalid values MUST fail explicitly.
- **FR-011**: The stable filter contract MUST include optional page and slide coordinates; because line-based text
  blocks carry no such coordinates, these filters MUST match only blocks carrying the exact coordinate and MUST NOT be
  silently ignored.
- **FR-012**: The `search` and `reindex` commands MUST integrate with the installable `openardp` CLI using the shared
  workspace validation, human and versioned JSON envelopes, body-minimizing output and deterministic exit
  classifications.
- **FR-013**: Search responses MUST stay within documented bounds: result limit default 20 with accepted range 1–100,
  bounded snippet length and bounded query size; truncation MUST be reported explicitly rather than silently dropping
  hits.
- **FR-014**: Concurrent ingest and search MUST never expose index rows for uncommitted or superseded representations;
  readers MUST observe a consistent snapshot of searchable scope.
- **FR-015**: When the runtime cannot provide the mandated index capability, every index-dependent operation MUST fail
  closed with a sanitized capability classification before serving results.
- **FR-016**: Document text inside queries, snippets and filters MUST remain `role=data` with instruction execution
  disabled; no result rendering may initiate tool, shell, network or filesystem side effects.
- **FR-017**: Default logs, diagnostics and errors MUST contain bounded identifiers, classifications and timings only,
  not query payloads beyond bounded classifications, snippets or document bodies.
- **FR-018**: Every public index, search, catalog and CLI contract plus each persisted behavior and security boundary
  introduced by F005 MUST have deterministic synthetic offline tests.
- **FR-019**: F005 MUST remain bounded to exact lexical retrieval: embeddings, semantic or fuzzy matching, OCR,
  summarization, rich-document coordinates beyond the stable filter surface, watchers, MCP, HTTP and export are out of
  scope.

### Key Entities

- **Search Index Entry**: One derived, invalidatable lexical row for one normalized block of one ready representation;
  it is never authoritative and can always be rebuilt from verified evidence.
- **Search Query**: Bounded operator input of terms and quoted phrases with optional scope filters; it is untrusted
  input validated before execution.
- **Search Hit**: Body-minimizing evidence reference with rank, bounded snippet, block handle, block kind, trust
  classification, representation scope and exact line provenance.
- **Index Coverage Report**: Deterministic comparison between catalog projections and index rows used to detect
  missing, orphaned or stale derived state.
- **Backfill Report**: Bounded per-scope outcome of the explicit one-time index population for pre-feature
  representations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After ingesting the synthetic TXT and Markdown fixtures, term and phrase searches return exactly the
  expected current blocks with references that validate against committed catalog facts and verified persisted
  content in 100 percent of cases.
- **SC-002**: Across at least 20 repeated identical queries on a fixed corpus, hit sets, order and snippets are
  byte-identical; at least 8 concurrent queries during an ingest observe either the complete old or the complete new
  searchable scope, never a mixture.
- **SC-003**: A source change that supersedes a version removes its blocks from default results in the same commit that
  makes the new version searchable, and the explicit history option restores them with exact version identity.
- **SC-004**: Fault injection at every index commit boundary yields zero partially searchable ready representations,
  and coverage verification detects 100 percent of deliberately missing, orphaned and stale rows in the synthetic
  corpus.
- **SC-005**: Backfilling a workspace with pre-feature representations makes exactly their current ready blocks
  searchable, is a no-op when repeated, and leaves every persisted representation and original file byte-identical.
- **SC-006**: The negative corpus of malformed queries, operator lookalikes, invalid filters and hostile document text
  causes zero SQL errors leaking internals, zero side effects and zero network calls, each with a stable
  classification.
- **SC-007**: Human and JSON forms of `search` have deterministic integration tests through the installed entry point;
  JSON hits validate the documented envelope and no search response includes full block bodies.
- **SC-008**: The full locked repository gates pass offline on Python 3.12 and the complete suite passes on Linux,
  macOS and Windows CI.

## Assumptions

- SQLite FTS5 is the mandated local index mechanism (constitution, architecture and feature map); availability is
  probed at runtime and treated as a fail-closed capability.
- Relevance ordering uses the index's documented built-in ranking on a fixed corpus plus a total deterministic
  tie-break; no learned or provider-dependent ranking exists in F005.
- A deterministic local benchmark for the documented search latency target belongs to the benchmark feature; F005 only
  keeps query execution bounded and indexed, without claiming measured performance evidence.
- Line-based text blocks carry no page or slide coordinates; the coordinate filters are contractually stable and
  currently match only blocks that explicitly carry them.
- Snippets are bounded derived text windows around matches and, like outline labels, are the documented exception to
  body-minimizing output; full bodies still require `get`.
- Search is a local read operation; it does not schedule background workers, watchers or daemons.

## Dependencies

- Converged F001 repository, packaging and three-platform quality gates.
- Converged F002 models, schemas and RFC 8785 identity helpers.
- Converged F003 immutable CAS, transactional SQLite catalog, ordered checksummed migrations and durability profile.
- Converged F004 workspaces, deterministic text parsing, atomic ready representations and the installable CLI.
- OpenARDP constitution, `AGENTS.md`, accepted ADRs 0002 and 0006, and the architecture/security/test documents.

## Out of Scope

- Embeddings, semantic retrieval, fuzzy matching, spell correction, learned ranking and any model/provider call.
- OCR, captions, summaries, translations and other derived enrichment.
- PDF/DOCX/PPTX indexing, bounding boxes and page-image evidence (beyond the stable coordinate filter surface).
- Reconciliation of blocks or index reuse across changed source versions.
- Watchers, background indexing daemons, scheduled jobs and remote or multi-user search.
- MCP, HTTP, cloud connectors, telemetry and portable package export/import.
