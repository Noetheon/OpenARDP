# Feature Specification: Redistributable Real-World Corpus

**Feature Branch**: `codex/f024-redistributable-realworld-corpus`

**Created**: 2026-08-02

**Status**: Clarified; planning pending

**Input**: Add a licensed, realistic and independently reproducible multi-format corpus for offline OpenARDP evaluation.

## Clarifications

### Session 2026-08-02

- Q: May a missing format be represented by a generated conversion of another source? → A: No. Each of the six payloads
  is an original publisher-distributed file in its declared format; conversions are derived data and cannot satisfy the
  corpus-selection requirement.
- Q: Should the CISA KEV data follow the live catalog? → A: No. F024 pins one full official repository commit and exact
  bytes. Freshness against the live operational catalog is outside this benchmark and never changes the snapshot.
- Q: Does automated rights validation prove legal permission? → A: No. It proves declared facts, identities and mapping
  completeness. Human review assertions, trademark/non-endorsement limits and the absence of legal advice remain
  explicit in every outward-facing result.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Use One Real Offline Corpus (Priority: P1)

As a maintainer or evaluator, I can use a small versioned corpus of genuine public documents covering PDF, DOCX, PPTX,
CSV, Markdown and plain text without downloading anything or generating artificial document bodies.

**Why this priority**: F020 measured synthetic structure and explicitly could not establish real-world document quality.
A committed corpus is the prerequisite for repeatable parsing and the later semantic evaluation.

**Independent Test**: On a disconnected clean checkout, verify the closed corpus tree and reconcile every asset's exact
bytes, media type and stable corpus identity from the committed lock.

**Acceptance Scenarios**:

1. **Given** a clean checkout with no network, **When** corpus validation runs, **Then** all six required formats and only
   the locked files are available with exact byte identities.
2. **Given** one missing, changed, extra, linked or case-colliding file, **When** validation runs, **Then** the corpus is
   rejected before parsing and no partial valid result is returned.
3. **Given** identical corpus bytes at another absolute path, **When** identity is computed, **Then** the corpus ID is
   identical and contains no host-specific state.

---

### User Story 2 - Audit Redistribution and Provenance (Priority: P1)

As a downstream redistributor, I can inspect who published every asset, where the exact source came from, why
redistribution was accepted and which attribution, trademark or non-endorsement limits still apply.

**Why this priority**: A checksum establishes identity but not permission. A sustainable benchmark must retain both
mechanically verified facts and review assertions without presenting either as legal advice.

**Independent Test**: Reconcile each payload to exactly one source record, rights basis and notice; reject missing,
ambiguous or conflicting mappings and independently compare the retained upstream metadata facts.

**Acceptance Scenarios**:

1. **Given** any corpus asset, **When** its lock entry is inspected, **Then** it identifies title, publisher, authors or
   responsible organization, publication date, exact source URL/revision, rights-evidence URL, SHA-256 and byte length.
2. **Given** a NASA asset, **When** redistribution facts are reviewed, **Then** the corresponding NTRS record states
   public use is permitted and reports no third-party material; NASA marks and non-endorsement remain separate limits.
3. **Given** a CISA asset, **When** redistribution facts are reviewed, **Then** the exact Git commit and CC0 dedication
   are retained with the complete notice text.
4. **Given** complete records, **When** validation succeeds, **Then** the result is described as mechanical and reviewed
   evidence rather than legal certainty or publisher endorsement.

---

### User Story 3 - Reproduce Exact Source Bytes Explicitly (Priority: P1)

As an independent maintainer, I can explicitly fetch the selected public sources into a fresh destination and prove they
match the committed corpus, while upstream drift or outage fails closed and leaves the repository unchanged.

**Why this priority**: A vendored corpus alone is inspectable but not independently reproducible from its publishers.
Conversely, mutable live URLs alone cannot freeze an experiment.

**Independent Test**: Fetch all assets into two fresh external roots, compare exact file and corpus identities with the
committed lock and corpus, then substitute a changed response and verify that publication is refused.

**Acceptance Scenarios**:

1. **Given** explicit network authorization and reachable reviewed hosts, **When** reproduction completes, **Then** a
   fresh closed tree matching the committed corpus ID is atomically published outside the repository.
2. **Given** a changed, truncated, oversized, redirected or unavailable response, **When** reproduction runs, **Then** it
   fails without replacing an existing destination or accepting new bytes.
3. **Given** ordinary import, test, validation, ingestion or benchmark use, **When** it executes, **Then** no corpus
   download, update check or other network access occurs.

---

### User Story 4 - Establish a Six-Format Parsing Baseline (Priority: P1)

As a product evaluator, I can run every real document through a delivered OpenARDP parser or an explicitly bounded
benchmark-only structural probe offline and obtain body-free evidence about success, provenance, output structure,
determinism, time and memory.

**Why this priority**: File availability does not prove the product can ingest the files or preserve useful evidence.
This baseline closes the structural real-world gap while leaving semantic judgments for F025.

**Independent Test**: With sockets denied, a validated F023 PDF bundle and fresh workspaces, ingest all six assets twice,
verify source/native/block identities and anchors, then independently regenerate the result and decision from raw facts.

**Acceptance Scenarios**:

1. **Given** a valid corpus and offline PDF bundle, **When** the baseline runs, **Then** all six assets ingest successfully
   with exact source identity, provider-native evidence and at least one retrievable block.
2. **Given** two fresh runs of identical inputs and recipes, **When** accepted evidence is compared, **Then** source,
   native and ordered block identities are deterministic for every asset.
3. **Given** retained raw observations, **When** an independent validator runs, **Then** it recomputes inventory,
   summaries, correctness judgments, result identities and the final baseline decision without trusting report prose.
4. **Given** any parser failure, network attempt, resource breach, identity mismatch or missing anchor, **When** the result
   is generated, **Then** that unfavorable fact remains visible and the corpus is not labelled baseline-ready.

---

### User Story 5 - Preserve a Stable Evaluation Boundary (Priority: P2)

As a future benchmark author, I can depend on a versioned, change-controlled corpus contract and can distinguish corpus
changes from parser or semantic-system changes.

**Why this priority**: Quiet edits to samples or ground truth invalidate comparisons and encourage overclaiming.

**Independent Test**: Change any locked byte, metadata assertion or result observation and prove drift checks fail until a
new corpus version and explicit review record are introduced.

**Acceptance Scenarios**:

1. **Given** a committed corpus version, **When** any payload or identity-bearing lock field changes, **Then** validation
   fails unless the corpus version and review evidence are deliberately advanced.
2. **Given** the F024 baseline, **When** its report is read, **Then** it makes no claim about answer correctness, semantic
   relevance, ranking quality, citation quality or general document-population accuracy.
3. **Given** F025 is implemented later, **When** it references the corpus, **Then** it pins the exact F024 corpus ID rather
   than silently following a mutable directory.

### Edge Cases

- A source URL is stable in appearance but its bytes change or an upstream repository branch advances.
- A source host redirects across domains, returns HTML, truncates a response or streams beyond the declared bound.
- A corpus root contains symlinks, hard-link aliases, special files, Unicode-normalization or case-fold collisions.
- Office ZIP containers contain unusual embedded media, macros, external relationships or content that resembles tool
  instructions; all remain untrusted parser input and never become execution authority.
- A NASA record changes its rights metadata while the document bytes remain unchanged.
- An asset is mechanically valid but its rights assertion, source metadata or required notice is missing.
- The PDF bundle is absent, invalid or valid but its provider tries to use a cache or network.
- Different parser platforms retain equivalent accepted evidence while timing and provider-internal details differ.
- The public CISA catalog grows after the pinned snapshot and no longer matches current operational reality.
- The corpus is too small to support a generalization claim even though every selected file parses successfully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST contain one versioned corpus with exactly six genuine public-sector payloads: one each
  of PDF, DOCX, PPTX, CSV, Markdown and plain text.
- **FR-002**: Payload bytes MUST be retained unchanged from their reviewed publisher source; generated conversions,
  normalized rewrites or reconstructed equivalents MUST NOT replace originals.
- **FR-003**: The corpus MUST combine an AI/open-science NASA NTRS document set with a pinned CISA Known Exploited
  Vulnerabilities repository snapshot so the workload contains prose, slides, tables and operational records.
- **FR-004**: Every payload MUST declare a stable relative path, media type, SHA-256, exact byte length, title, publisher,
  responsible authors/organization, publication date, source record URL and exact download URL or revision.
- **FR-005**: Every payload MUST map to one explicit reviewed rights basis and required notice; missing, conflicting,
  ambiguous or unreviewed rights assertions MUST fail validation.
- **FR-006**: NASA records MUST retain NTRS copyright determination, third-party-material flag and metadata snapshot;
  CISA records MUST pin a full Git commit and retain the CC0 text used by that revision.
- **FR-007**: Rights documentation MUST distinguish byte/provenance verification, human review assertion, trademark or
  agency-mark limits, non-endorsement and legal advice.
- **FR-008**: The corpus lock MUST use JSON Schema 2020-12-compatible fields and a canonical RFC 8785/SHA-256 identity
  independent of absolute paths, host state and timestamps.
- **FR-009**: Offline validation MUST reject missing, extra, linked, non-regular, duplicate, traversal, normalization-
  colliding, case-colliding, length-mismatched, digest-mismatched and undeclared files.
- **FR-010**: Offline validation MUST reconcile exactly one source and rights record per payload and MUST verify retained
  metadata/license snapshot identities without importing any parser provider.
- **FR-011**: Connected reproduction MUST be an explicit maintainer action, use only HTTPS reviewed hosts and fixed
  source revisions where available, enforce redirects/response type/per-file/aggregate bounds and stream into staging.
- **FR-012**: Reproduction MUST verify length and SHA-256 before absent-destination atomic publication and MUST never
  mutate committed assets, overwrite a destination or accept drifted upstream bytes.
- **FR-013**: Package installation, imports, unit tests, validation and ordinary product operation MUST perform no corpus
  download, update check, telemetry or other network access.
- **FR-014**: All corpus content MUST be treated as untrusted document data; embedded instructions, links, macros or
  relationships MUST NOT initiate tools, fetches or side effects.
- **FR-015**: A versioned baseline MUST parse the five core-supported formats through delivered provider profiles and
  MUST process CSV through a separate isolated body-free structural probe with sockets denied; PDF MUST use only a
  separately validated F023 offline bundle. The CSV probe MUST NOT be described as a stable product ingestion API.
- **FR-016**: Each observation MUST retain only body-free identifiers and measurements: asset/source/native/recipe/block
  identities, format, counts, anchor classes, bytes, wall/CPU time, peak RSS, stable outcome and error category.
- **FR-017**: Repeated fresh ingestion MUST compare exact accepted source, native and ordered block identities; platform-
  specific timings and non-contractual provider internals MUST NOT be used as determinism criteria.
- **FR-018**: The baseline MUST verify that each accepted block is retrievable by identity and has a source/evidence
  anchor appropriate to its format; it MUST not evaluate semantic relevance or answer quality.
- **FR-019**: An independent validator MUST recompute corpus/result identities, closed observation coverage, aggregate
  statistics, correctness judgments and the final decision from raw retained facts rather than report prose.
- **FR-020**: The final decision MUST fail closed if any format is missing, corpus validation fails, network is attempted,
  ingestion fails, required evidence is absent, identities differ or declared resource bounds are exceeded.
- **FR-021**: Results MUST distinguish selection validity, redistribution review, reproducibility, parser baseline and
  generalization limits; success MUST NOT imply legal certainty or broad real-world document quality.
- **FR-022**: Unit and cross-platform CI tests MUST remain offline and use small synthetic stand-ins for producer fault
  injection; committed real payloads may be validated and non-PDF formats parsed without network or hidden downloads.
- **FR-023**: Actual six-format/PDF measurement MAY be an explicit reference run outside ordinary CI, but its frozen raw
  facts and independent drift validation MUST be committed.
- **FR-024**: Corpus payloads and reports MUST contain no secrets, credentials, private personal records, hostnames,
  usernames, absolute paths, cache contents, raw exceptions or newly generated document-body copies.
- **FR-025**: F020 synthetic evidence and F023 PDF readiness history MUST remain unchanged; F024 adds a distinct real-
  corpus baseline and MUST NOT rewrite earlier outcomes.
- **FR-026**: Semantic questions, answer generation, retrieval ranking, relevance grading and source-quality scoring MUST
  remain out of scope for F024 and belong exclusively to F025.

### Non-Goals and Compatibility Impact

- **Non-goal**: Claim that six selected documents represent all organizations, languages, layouts or document quality.
- **Non-goal**: Build a question-answering system, embedding index, relevance ranker or semantic ground truth.
- **Non-goal**: Track the live CISA catalog or silently update any source.
- **Non-goal**: Modify parser contracts, persisted identifiers, workspace schema or PDF provider behavior.
- **Compatibility impact**: Additive corpus, maintainer reproduction/validation tools and body-free benchmark evidence;
  no product-runtime migration or default network/dependency change.

### Key Entities

- **Corpus Lock**: Versioned canonical selection, identity, paths, byte facts, source facts and rights mappings.
- **Corpus Asset**: Exact unmodified publisher payload treated as untrusted input.
- **Source Metadata Snapshot**: Minimal retained publisher/repository facts used to audit provenance and rights drift.
- **Rights Record**: Reviewed basis, evidence link, notice, non-endorsement and open-limit assertion.
- **Reproduction Observation**: Body-free outcome of one explicit connected fetch and exact verification.
- **Parsing Baseline Run**: Frozen offline observations, aggregate results and fail-closed decision for one corpus ID.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The validated corpus contains exactly six payloads and all six required formats, with zero extra, linked or
  mechanically unverified files and an aggregate payload size no greater than 16 MiB.
- **SC-002**: Independent validation detects 100% of the defined missing, extra, link, collision, truncation, length,
  digest, rights-mapping and metadata/license-snapshot tamper cases.
- **SC-003**: Every payload maps to exactly one reviewed authoritative source and rights record; the three NASA records
  report public-use permission and no third-party material, and the three CISA files map to one full commit and CC0 text.
- **SC-004**: Two explicit reproductions into fresh roots produce the exact committed payload hashes and corpus ID, or
  retain a clear fail-closed upstream-drift/outage result without publishing a destination.
- **SC-005**: All six genuine payloads are structurally processed with sockets denied on the binding environment, return
  at least one verified retrievable unit and at least one appropriate evidence anchor, and emit no network attempt; the
  result distinguishes the benchmark-only CSV probe from core product ingestion.
- **SC-006**: Two fresh accepted ingestions per asset produce identical source, native and ordered block identities.
- **SC-007**: No individual ingestion exceeds the existing 120-second worker timeout or 4 GiB address-space bound; exact
  wall/CPU/RSS measurements are reported as environment- and workload-bounded observations.
- **SC-008**: The independent result validator reproduces all observations, summaries, identities, judgments and the
  `REALWORLD_BASELINE_READY` or `REALWORLD_BASELINE_NOT_READY` decision exactly.
- **SC-009**: A clean cross-platform repository run passes existing quality gates without network/model downloads, while
  the explicit reference run remains reproducible with the separately provisioned F023 bundle.
- **SC-010**: Public documentation states the corpus selection, exact rights/reproducibility evidence and limits, and
  makes zero semantic-answer, population-wide-quality, legal-certainty or endorsement claims.

## Assumptions

- NTRS per-record public-use and third-party-material fields are the primary selection evidence for NASA assets; retained
  metadata captures the reviewed observation but cannot prevent later publisher metadata changes.
- The CISA KEV GitHub mirror is an official agency repository whose selected full revision retains a CC0 dedication.
- NASA and CISA names, insignia and marks are not granted as product branding; redistribution is informational and does
  not imply endorsement.
- The six-file corpus is deliberately small enough for repository distribution and repeatable local evaluation; its
  breadth limitation is a finding, not a hidden assumption.
- The F023 reference model bundle remains external to Git and is supplied explicitly for the binding PDF run.
