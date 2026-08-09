# Feature Specification: Context Compiler and Selection Receipts

**Feature Branch**: `codex/f008-context-bundles`

**Created**: 2026-07-26

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Compile bounded, version-pinned evidence for a task and emit a
deterministic, privacy-conscious receipt explaining every selection, omission,
rejection, stale item and unit of budget.

## Clarifications

### Session 2026-07-26

- Q: What corpus state is authoritative for compilation and replay? → A: The initial
  request resolves current document heads to an exact sorted snapshot; replay uses only
  those recorded version/representation scopes and fails on drift or missing evidence.
- Q: What does the budget cover? → A: The declared limit covers the complete serialized
  context bundle plus a 10% response reserve. A further 10% provenance target is
  accounted explicitly; the body-free receipt is outside the handoff budget.
- Q: What selection strategy is in scope? → A: A deterministic lexical baseline over
  verified text blocks and F007 rich projections only. Model rankers, embeddings,
  summaries and semantic-equivalence claims are deferred.
- Q: How privacy-conscious is the receipt? → A: It records a task digest, exact policy,
  scope, identities, costs and reason codes, but no query text, evidence body, source
  path, secret or credential.
- Q: What happens when requested visual evidence is unavailable? → A: The compiler emits
  explicit missing-evidence and visual-escalation notices; F008 never invents visual
  detail or implements the F011 extraction path.

## User Scenarios & Testing

### User Story 1 - Compile Bounded Evidence (Priority: P1)

As a local user, I can compile the smallest useful, exact evidence set for a task across
selected current documents without exceeding the declared budget or treating document
content as instruction.

**Why this priority**: A bounded evidence handoff is the core product capability that
turns verified ingestion and retrieval into useful progressive context.

**Independent Test**: Ingest one text document and one rich document, compile a task
against both under a small budget, and verify that the result contains exact
version-pinned evidence, deterministic order, explicit trust delimiters and accounting
that never exceeds the limit.

**Acceptance Scenarios**:

1. **Given** current verified text and rich document representations, **When** a user
   compiles a lexical task for both documents, **Then** the result pins each exact source
   and representation version, selects matching verified evidence in total deterministic
   order and persists an immutable context bundle plus receipt.
2. **Given** evidence text that resembles a system prompt, URL, command or tool request,
   **When** it is selected, **Then** it is enclosed and labelled as untrusted data and
   triggers no side effect, path resolution, network request or instruction execution.
3. **Given** a budget too small for every candidate, **When** compilation completes,
   **Then** the complete serialized context bundle and response reserve fit the limit,
   and every unselected high-value candidate is visible in the receipt.
4. **Given** a numeric, verification or visual task whose required evidence type is
   unavailable, **When** compilation completes, **Then** the bundle reports exact missing
   evidence rather than substituting a summary or invented detail.

---

### User Story 2 - Explain and Replay Selection (Priority: P2)

As an auditor, I can inspect a body-free receipt and replay the exact compilation so I
can understand why evidence was selected, omitted, rejected or classified stale.

**Why this priority**: Determinism without an auditable explanation is insufficient for
evidence-sensitive use and regression diagnosis.

**Independent Test**: Compile the same task twice and replay its stored receipt with an
unchanged corpus, then compare bundle and receipt identities and every ordered decision.

**Acceptance Scenarios**:

1. **Given** identical task bytes, exact corpus snapshot, policy, limits, algorithm and
   tokenizer identity, **When** compilation or replay runs repeatedly, **Then** the
   selected order, accounting, bundle identity and receipt identity are identical.
2. **Given** a stored receipt, **When** it is inspected, **Then** it exposes the task
   digest, policy digest and values, exact corpus snapshot, tokenizer and algorithm
   versions, budget ledger, ordered selections, omissions, rejection reasons, stale
   items, truncation and missing-evidence notices without exposing source bodies or
   secrets.
3. **Given** a tokenizer, algorithm or policy version mismatch, **When** replay is
   requested, **Then** replay fails with one stable mismatch category and returns no
   misleading substitute result.
4. **Given** an exact snapshot whose objects still exist after a newer document head is
   committed, **When** replay runs, **Then** it uses the recorded snapshot rather than
   silently selecting from the newer head.

---

### User Story 3 - Fail Closed on Integrity and Lifecycle Faults (Priority: P3)

As an operator, I receive a bounded, sanitized failure instead of partial or stale
context when an index, catalog fact, object, derivation or compilation is unsafe.

**Why this priority**: Context is a security-sensitive handoff and cannot amplify a
corrupted accelerator or stale derived assertion.

**Independent Test**: Inject index drift, CAS/catalog corruption, stale candidates,
publication failure and cancellation at each selection phase; verify no invalid
compilation becomes reachable and an earlier valid compilation remains unchanged.

**Acceptance Scenarios**:

1. **Given** incomplete, orphaned or drifted lexical-index coverage, **When** compilation
   requests affected text evidence, **Then** it fails closed with an explicit
   accelerator-integrity category and does not trust indexed bodies or metadata.
2. **Given** a stale derived candidate, mismatched scope, invalid trust promotion,
   unverifiable body or unsupported representation, **When** candidates are evaluated,
   **Then** they are excluded and recorded with stable body-free reasons.
3. **Given** cancellation before publication, **When** compilation stops, **Then** no
   catalog-visible compilation is created and any pre-published immutable object remains
   only an unreachable recovery candidate.
4. **Given** a failure while atomically recording the bundle and receipt, **When** the
   operation is retried, **Then** the retry converges on the same valid identities and no
   partial compilation is observable.

---

### User Story 4 - Use Stable Local CLI Workflows (Priority: P4)

As a local user or script, I can compile context and inspect a receipt through bounded
human-readable and versioned JSON command output.

**Why this priority**: CLI access makes the service directly usable and supplies the
stable application boundary that F009 can wrap without moving business logic into MCP.

**Independent Test**: Run the context and receipt commands in a fresh local workspace
for success, empty result, tiny budget, mismatch, corruption and cancellation cases and
validate their stable output envelopes.

**Acceptance Scenarios**:

1. **Given** registered document identifiers, a task and a valid budget, **When** the
   context command runs, **Then** JSON output returns bounded bundle/receipt handles and
   accounting while human output summarizes selections and warnings without dumping the
   receipt's source bodies.
2. **Given** a receipt identifier, **When** the receipt command runs, **Then** it returns
   the exact verified body-free receipt in deterministic JSON order.
3. **Given** an empty corpus, empty task, invalid identifier, unsupported tokenizer,
   invalid policy or budget below the minimum envelope, **When** a command runs, **Then**
   it uses the existing sanitized error envelope and creates no compilation.

### Edge Cases

- The corpus contains zero documents, a document without a current READY head, mixed text
  and rich heads, duplicate document identifiers, or more scopes than the declared cap.
- A query contains duplicate terms, quotes, Unicode, control characters, prompt
  injection, path-like text, URLs or the maximum accepted number of lexical items.
- No candidate matches, every candidate is stale/rejected, the base metadata alone
  exceeds budget, or the final accepted item fits exactly at the boundary.
- Multiple candidates have identical lexical relevance, estimated cost or evidence
  identity; ordering remains total without timestamps or randomized values.
- A rich projection body is structured JSON, very large, duplicated across anchors or
  valid but unsupported for the requested evidence type.
- A source head changes after snapshot resolution, a historical snapshot remains valid,
  or one historical object becomes missing/tampered before replay.
- Cancellation occurs before retrieval, during candidate verification, after CAS
  publication or immediately before catalog commit.
- A receipt, bundle or catalog row is non-canonical, references mismatched objects or
  contains a receipt identity inconsistent with its deterministic projection.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST accept a non-empty task, bounded document corpus, byte,
  character or token budget, exact tokenizer/estimator identity, answer mode, required
  evidence types, freshness policy and trust policy.
- **FR-002**: Initial compilation MUST resolve each requested current document to one
  exact `{document_id, version_id, representation_id}` snapshot before candidate
  retrieval, deduplicate and sort that snapshot, and reject missing or non-READY scopes.
- **FR-003**: Replay MUST use the exact recorded corpus snapshot and MUST NOT silently
  substitute a newer head, different recipe or missing representation.
- **FR-004**: Candidate discovery MUST use only the deterministic lexical baseline over
  verified authoritative text blocks and F007 rich evidence projections; optional model,
  embedding, summary and reranking paths MUST remain disabled and outside this feature.
- **FR-005**: Accelerator coverage, mapping and returned evidence MUST be verified against
  exact catalog and content-addressed facts before selection; drift, corruption or
  incomplete coverage MUST fail closed and MAY be repaired only through the existing
  explicit rebuild command.
- **FR-006**: Every candidate MUST carry an exact evidence identity, source/native scope,
  representation type, trust/sensitivity classification, freshness, deterministic score
  key, verified body handle and estimated inclusion cost.
- **FR-007**: Selection ordering MUST be total, documented and independent of wall-clock
  time, process-randomized values, database row order and model inference.
- **FR-008**: The compiler MUST enforce explicit corpus, candidate, body, receipt,
  decision and budget limits before allocating or returning unbounded content.
- **FR-009**: The budget ledger MUST account for the complete serialized context bundle,
  with a 10% response reserve and explicit provenance target, using the exact declared
  tokenizer/estimator version; the returned estimate MUST never exceed the declared
  limit.
- **FR-010**: Selected source bodies MUST be structurally delimited and labelled as
  untrusted role `data`; compilation MUST NOT execute or resolve document text as a
  command, URL, path, import, policy or tool request.
- **FR-011**: Numeric tasks MUST prefer exact text/table-cell evidence; verification tasks
  MUST preserve exact source/integrity facts; visual tasks MUST require a visual handle
  or emit an explicit F011 escalation/missing-evidence notice.
- **FR-012**: A stale derivation, mismatched scope, trust promotion, unsupported
  representation, unverifiable body or duplicate candidate MUST be excluded before
  selection and recorded with a stable body-free rejection/stale reason.
- **FR-013**: Every successful compilation MUST produce one additive experimental
  `ContextBundle 0.2.0` whose evidence provenance discriminates exact F002 blocks from
  exact F006 projections, and one independently versioned experimental
  `SelectionReceipt 0.1.0` that contains no query text, evidence body, absolute
  source/model path, secret or credential.
- **FR-014**: The receipt MUST record its deterministic identity, task digest, exact
  algorithm/config, tokenizer/estimator, complete policy, policy digest, corpus snapshot,
  budget ledger, selected order, omissions, rejections, stale items, truncation,
  high-value omissions and missing-evidence/escalation notices.
- **FR-015**: Receipt identity MUST be a versioned RFC 8785/SHA-256 projection over all
  semantic receipt fields; changing task, scope, policy, budget, tokenizer, algorithm or
  decisions MUST change the identity.
- **FR-016**: Context-bundle identity and ordering MUST be deterministic for identical
  semantic inputs; repeated compilation and replay MUST converge on byte-identical
  canonical bundle and receipt objects.
- **FR-017**: Complete bundle and receipt bytes MUST be immutable content-addressed
  objects and MUST become catalog-reachable together in one atomic, idempotent commit.
- **FR-018**: Catalog evolution MUST be append-only, checksummed, transactional,
  structurally validated and reject incompatible, gapped, drifted or newer workspaces.
- **FR-019**: Publication, catalog and cancellation failures MUST expose no partial
  compilation; retry MUST either reuse the exact complete result or fail without
  mutating an earlier valid result.
- **FR-020**: Receipt and bundle reads MUST verify object digest, length, canonical JSON,
  public model validity, deterministic identities, row/object agreement and referenced
  exact scopes before return.
- **FR-021**: Cancellation MUST be checked at bounded phases, produce a stable sanitized
  category and prevent catalog commit; durable queued-job cancellation remains F012.
- **FR-022**: Default logs, CLI errors and diagnostics MUST include only identifiers,
  counts, phases, reason codes and timings, never task text, evidence/native bodies,
  source paths, secrets or tracebacks.
- **FR-023**: The CLI MUST add bounded context compilation and exact receipt inspection
  while preserving all existing text/rich ingest, search, evidence and query behavior
  and stable JSON envelopes.
- **FR-024**: The provider-neutral compiler service MUST contain no Docling, MCP, cloud,
  model-provider or arbitrary filesystem dependency; F009 wraps the same application
  service without moving selection logic.
- **FR-025**: All changed behavior, public contract, identity, migration, budget, privacy,
  accelerator, cancellation, replay and failure paths MUST have synthetic,
  network-disabled tests on Linux, macOS and Windows.
- **FR-026**: Public documentation MUST describe exact commands, budget semantics,
  selection ordering, privacy, compatibility, migration, rollback, known limits and
  residual risks without claiming universal quality, performance, security or token
  accuracy.
- **FR-027**: The new ContextBundle `0.2.0` and SelectionReceipt `0.1.0` schemas MUST use
  JSON Schema 2020-12, exact experimental version support, closed direct fields,
  JSON-only extensions, deterministic generation, valid/invalid fixtures and independent
  identity vectors.
- **FR-028**: Existing nine public schemas, their identity vectors, F006 conformance
  corpus and previous behavior MUST remain byte-for-byte and semantically unchanged.

### Non-Goals and Compatibility Impact

- **Non-goal**: No LLM/model/embedding ranker, generated summary, answer generation,
  semantic equivalence or mandatory vector capability.
- **Non-goal**: No visual extraction/cropping, OCR escalation or image payload; only
  explicit F011 escalation/missing-evidence notices.
- **Non-goal**: No MCP or HTTP interface, write-capable tool, watcher, durable scheduler,
  derivation DAG, garbage collection or export/import format.
- **Non-goal**: No automatic index repair during compilation and no universal tokenizer
  accuracy claim.
- **Compatibility impact**: Additive experimental public `ContextBundle 0.2.0` and
  `SelectionReceipt 0.1.0` contracts, additive application/CLI surface and checksummed
  workspace migration 6. Existing `ContextBundle 0.1.0` and the other eight public
  schema bytes/readers remain unchanged and available. Provider/export profiles are
  unchanged; the new minor bundle release has independent fixtures/migration notes and
  is additive rather than a silent same-version change.

### Key Entities

- **Context Compile Request**: Task plus bounded corpus, exact budget/estimator, mode,
  evidence, freshness and trust policy inputs.
- **Corpus Snapshot**: Sorted unique exact document/source/representation scopes used for
  discovery and replay.
- **Context Candidate**: Body-minimizing verified evidence option with exact scope,
  representation, trust, freshness, deterministic score and estimated inclusion cost.
- **Budget Ledger**: Total limit, response reserve, provenance target, base bundle cost,
  selected cost and final exact bundle usage in one declared unit.
- **Selection Receipt**: Privacy-conscious body-free deterministic audit record of the
  complete input policy, corpus and selection lifecycle.
- **Context Compilation**: Immutable catalog linkage between one receipt object, one
  context-bundle object and all exact snapshot roots.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The reviewed mixed text/rich quickstart produces one verified bundle and
  receipt with at least one exact evidence item from each matching document and zero
  network calls.
- **SC-002**: Across 20 identical compilations and five receipt replays, bundle bytes,
  receipt bytes, identities, selected order, omissions and accounting are identical.
- **SC-003**: In 100% of boundary cases, final bundle usage plus response reserve is at
  or below the declared limit; the exact-fit case succeeds and one-unit overflow is
  omitted or rejected.
- **SC-004**: Every discovered candidate appears exactly once as selected, omitted,
  rejected or stale, and all high-value omissions are explicitly labelled.
- **SC-005**: Task/query text and evidence bodies appear zero times in reviewed receipt
  JSON, default logs and error envelopes.
- **SC-006**: All selected evidence and returned compilation objects pass full
  digest/length/canonical/model/scope/identity verification before return.
- **SC-007**: Every injected index, CAS, catalog, trust, scope, tokenizer, algorithm,
  publication and cancellation fault yields zero partial catalog-visible compilations.
- **SC-008**: Numeric/verification tasks never satisfy required exact evidence using a
  summary, and visual tasks without a handle always expose missing/escalation evidence.
- **SC-009**: Empty corpus/task, unsupported estimator, stale-only corpus, no-match,
  undersized budget and over-limit corpus cases all return stable documented outcomes.
- **SC-010**: The eleven public schemas, new bundle/receipt fixtures and identity vectors
  regenerate byte-identically in two consecutive runs, while all nine earlier schema and
  vector files remain byte-identical to the F007 base.
- **SC-011**: The provider-free core can import, compile synthetic candidates and validate
  receipts without Docling or any network/model dependency.
- **SC-012**: The full locked gate passes on Linux, macOS and Windows with at least 85%
  branch coverage, no tracked-file drift and successful source/wheel builds.

## Assumptions

- The local MVP remains single-user, single-workspace and explicitly scoped by registered
  document identifiers.
- Current-head resolution is a convenience only; all compilation authority is the exact
  snapshot recorded before retrieval.
- Existing F005 lexical indexes cover normalized text representations. Accepted F007
  rich evidence is provider-free and may use bounded verified lexical scanning until a
  later disposable rich-index feature is justified.
- The default token estimator deliberately overestimates one token per UTF-8 byte and is
  versioned honestly; callers needing a provider tokenizer must supply an exact local
  deterministic implementation with matching identity.
- Receipt retention follows immutable workspace reachability. Deletion/retention policy
  belongs to F013.
- Historical exact snapshots remain replayable only while their authoritative CAS and
  catalog roots pass verification.
