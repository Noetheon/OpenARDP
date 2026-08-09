# Feature Specification: Alternate Parser Conformance Spike

**Feature Branch**: `codex/f016-alternate-parser-conformance-spike`

**Created**: 2026-08-01

**Status**: Converged — see the [authoritative feature map](../../spec-kit/FEATURE_MAP.md)

**Input**: Authoritative Feature 016 prompt
`spec-kit/feature-prompts/016-alternate-parser-conformance-spike.md` (SHA-256 to be
recorded in implementation notes), plus the request to complete the project
sequentially with best-practice, long-lived and sustainable implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Independently Consume the Evidence Contract (Priority: P1)

As a contract maintainer, I can run an implementation that is isolated from the
OpenARDP runtime against the published evidence corpus so that structural and semantic
contract conformance is tested without relying on reference models or parser adapters.

**Why this priority**: Provider-neutrality is not meaningfully tested when the same
runtime that defines a contract is also the only implementation validating it.

**Independent Test**: Run the isolated consumer over the published manifest and verify
that it accepts every declared valid text, page and table example, rejects every declared
invalid example with a stable public category, and reproduces every declared identity.

**Acceptance Scenarios**:

1. **Given** the complete published evidence corpus, **When** the independent consumer
   evaluates it without access to OpenARDP packages or adapters, **Then** every expected
   valid/invalid outcome and identity digest agrees with the manifest.
2. **Given** valid text-span, page-region and table-cell references, **When** they are
   consumed, **Then** their exact source/native scope, bounds and identity remain intact.
3. **Given** a structurally valid record with a stale scope, impossible geometry,
   malformed pointer, trust escalation or identity drift, **When** it is consumed,
   **Then** it is rejected by a deterministic body-free category.

---

### User Story 2 - Produce Evidence with an Alternate Parser (Priority: P1)

As an integrator, I can parse small synthetic text and tabular sources with a non-Docling
producer and hand its records to the OpenARDP reference consumer so that the contract is
exercised in the opposite direction without embedding Docling concepts.

**Why this priority**: A consumer-only result can miss producer friction, especially
around provider profiles, native artifacts, anchors and identity construction.

**Independent Test**: Run the isolated producer twice on fixed text and tabular inputs,
compare byte-identical output, and validate its native representation plus text,
page-region and table-cell references with the reference implementation.

**Acceptance Scenarios**:

1. **Given** a synthetic text source, **When** the alternate producer parses it, **Then**
   it emits a retained native artifact and a text reference bound to the exact source and
   provider profile without any Docling-named field or value.
2. **Given** a synthetic tabular source with a declared page view, **When** the producer
   parses it, **Then** it emits table-cell and page-region references whose bounds and
   identities are accepted by the reference consumer.
3. **Given** identical source bytes and declared producer inputs, **When** production is
   repeated in separate isolated processes, **Then** the output bytes and all identities
   are identical.
4. **Given** untrusted instruction-shaped cell or text content, **When** it is parsed,
   **Then** it remains evidence data and cannot select commands, paths, trust or execution.

---

### User Story 3 - Make a Bounded Provider-Neutrality Decision (Priority: P1)

As an architecture reviewer, I receive a reproducible decision that separates verified
interoperability, contract friction, provider leakage, untested claims and required
changes so that public language does not exceed the evidence.

**Why this priority**: The spike is complete only when evidence changes an explicit
architecture claim; a passing demonstration must not silently stabilize an experimental
contract or imply semantic equivalence between parsers.

**Independent Test**: Regenerate the decision from the same corpus and alternate output,
then introduce a missing coverage class or failed vector and verify that the decision
changes to a failing outcome while preserving the recorded limitations.

**Acceptance Scenarios**:

1. **Given** complete successful bidirectional evidence, **When** the decision is built,
   **Then** it supports only the measured thin-contract claim and explicitly excludes
   universal semantic anchor equivalence, production readiness and standardization.
2. **Given** any required corpus class, identity vector, producer record or reference
   validation is absent or failing, **When** the decision is built, **Then** provider
   neutrality is not supported for that scope and no override converts absence to success.
3. **Given** observed friction or a Docling-specific assumption, **When** it is classified,
   **Then** the report traces it to an exact contract surface and states whether a contract,
   profile, fixture or claim change is required.
4. **Given** a non-breaking result, **When** the review completes, **Then** contract version
   and experimental stability remain unchanged and the lack of external-use and migration
   practice remains explicit.

### Edge Cases

- The isolated process can accidentally import OpenARDP or a globally installed dependency.
- A record passes JSON structure checks but fails a cross-record semantic invariant.
- An identity payload includes a number outside the supported interoperable integer domain,
  a floating-point value, non-NFC text or an unsupported canonicalization declaration.
- A manifest path escapes the fixture root, is absolute, duplicated, a symlink, too large
  or references an undeclared file.
- Text offsets split the declared view, page geometry exceeds fixed bounds, or a table
  coordinate is negative or outside the producer-declared grid.
- A provider pointer is syntactically acceptable but cannot be semantically dereferenced;
  the core must preserve it as opaque rather than invent equivalence.
- Two independently produced records reuse an identifier for different semantic payloads.
- Output order, line endings or locale differs across Linux, macOS and Windows.
- The alternate parser cannot represent an exact source feature without extending its
  provider-native payload.
- A successful narrow spike is misreported as a stable standard, external adoption,
  complete parser interchangeability or production-quality integration.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST provide an independent evidence-contract consumer that
  runs in a separate isolated process without importing OpenARDP runtime packages,
  reference models, parser adapters or third-party validation libraries.
- **FR-002**: The consumer MUST evaluate the complete published evidence-conformance
  manifest, not a hand-selected passing subset.
- **FR-003**: The consumer MUST validate closed record structure, supported contract
  versions, required field types, bounded values and namespaced extensions.
- **FR-004**: The consumer MUST independently enforce all semantic invariants required by
  the published corpus, including identity recomputation, source/native scope, anchor
  bounds, trust non-escalation and cross-record consistency.
- **FR-005**: The consumer MUST cover text-span, page-region, table-cell and opaque
  provider-pointer anchors; the measured minimum claim MUST include text plus page and
  table coverage.
- **FR-006**: Valid, invalid and identity-vector expectations MUST be declared in one
  deterministic manifest and every unexpected result MUST fail the run.
- **FR-007**: Invalid results MUST use stable body-free categories and MUST NOT expose
  source bodies, absolute paths or exception details.
- **FR-008**: Manifest and fixture reads MUST be confined to a declared root with bounded
  file counts and bytes; absolute paths, traversal, links and undeclared inputs MUST fail
  closed.
- **FR-009**: The feature MUST provide an alternate producer that parses fixed synthetic
  plain-text and tabular inputs without Docling or any OpenARDP parser adapter.
- **FR-010**: The producer MUST retain a complete immutable provider-native result and
  emit only thin evidence records needed for identity, navigation, retrieval, trust and
  lifecycle.
- **FR-011**: Producer records MUST use a clearly versioned non-Docling provider/profile
  identity and MUST NOT copy Docling-specific field names, class names or pointer grammar.
- **FR-012**: Producer output MUST include at least one native representation, text-span
  reference, page-region reference, table-cell reference and coherent thin projection.
- **FR-013**: Every producer record MUST bind to the exact source identity, source version,
  native representation, recipe and provider profile used to create it.
- **FR-014**: Producer output and identities MUST be byte-deterministic for identical
  normative inputs across repeat runs and supported platforms.
- **FR-015**: Alternate output MUST be consumed by the OpenARDP reference contracts, and
  reference output used by the alternate consumer, so evidence covers both directions.
- **FR-016**: Canonical identity processing MUST use the declared RFC 8785/SHA-256 envelope,
  reject unsupported JSON values and reproduce every published golden vector exactly.
- **FR-017**: Source and produced content MUST remain untrusted data and MUST never
  authorize execution, network activity, trust promotion or filesystem expansion.
- **FR-018**: Unit and integration validation MUST run without network access and use only
  synthetic or redistributable fixtures.
- **FR-019**: The conformance result MUST record exact corpus, schema, producer executable,
  source fixture and generated-output identities needed for reproducibility.
- **FR-020**: The decision MUST separately classify verified behavior, contract friction,
  provider leakage, limitations and required follow-up changes with traceable evidence.
- **FR-021**: Any missing or failed mandatory coverage MUST produce a failing decision;
  there MUST be no waiver, warning-only success or manual pass field.
- **FR-022**: Public claims MUST remain limited to the measured thin evidence-contract
  surface and MUST explicitly exclude semantic anchor equivalence, arbitrary parser
  interchangeability, external adoption and production readiness.
- **FR-023**: The feature MUST NOT stabilize the experimental contract solely because this
  internal spike passes; external-use evidence and migration practice remain outstanding.
- **FR-024**: If a contract change is required, the feature MUST classify compatibility,
  add migration evidence and follow existing ADR/version governance before publication.
- **FR-025**: Generated conformance output MUST be reproducible, drift-checked and portable
  across Linux, macOS and Windows.
- **FR-026**: The complete Spec Kit lifecycle, repository quality gates, distribution build
  and three-platform pull-request and post-merge workflows MUST pass before completion.

### Non-Goals and Compatibility Impact

- **Non-goal**: A production parser adapter, general CSV semantics, OCR, layout recovery,
  arbitrary file-format support, parser-quality comparison or provider migration tool.
- **Non-goal**: A claim that coordinates, text offsets, table structures or provider
  pointers are semantically interchangeable across arbitrary parsers.
- **Non-goal**: Contract stabilization, external standardization or evidence of adoption
  by an organization independent of this repository.
- **Compatibility impact**: Additive conformance evidence and tooling only. Evidence
  contract `0.1.0`, application version, workspace revision, provider profiles and export
  profiles remain unchanged unless the spike falsifies the current contract and an
  explicit governed migration is approved.

### Key Entities

- **Independent Consumer Result**: One expected-versus-observed corpus outcome with a
  stable category and exact fixture identity.
- **Alternate Native Representation**: The complete immutable result of the alternate
  text/tabular producer, bound to source and recipe identities.
- **Alternate Evidence Record Set**: Coherent thin references/projection produced under
  one non-Docling provider profile.
- **Conformance Observation**: An immutable fact binding implementation, input, expected
  outcome and observed outcome.
- **Provider-Neutrality Decision**: The fail-closed conclusion, evidence identities,
  verified scope, friction, leakage, limitations and required changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One isolated consumer processes 100% of the published valid, invalid,
  record-set and canonical-identity cases with zero unexpected outcomes.
- **SC-002**: Valid coverage includes all four anchor classes and the measured claim
  includes text, page-region and table-cell evidence.
- **SC-003**: The alternate producer emits the complete required record set for both
  synthetic sources and 100% of its records are accepted by the reference consumer.
- **SC-004**: Three repeated producer runs yield byte-identical output and identical
  record identities; the same expectation passes on Linux, macOS and Windows.
- **SC-005**: Attempts to access absolute, escaping, linked, undeclared or over-budget
  fixture inputs produce zero reads outside the declared conformance root.
- **SC-006**: Instruction-shaped source content produces zero tool calls, network
  attempts, trust promotions or output-path changes.
- **SC-007**: The generated decision can be reproduced byte-for-byte from declared
  normative inputs and fails when any mandatory observation is removed or changed.
- **SC-008**: Every reported friction/leakage/limitation item names an exact affected
  surface and disposition; no uncategorized finding remains.
- **SC-009**: A reviewer can run the focused end-to-end check from a clean checkout using
  one documented offline command and receive a stable pass/fail result.
- **SC-010**: All repository lint, formatting, strict typing, network-blocked tests,
  generated-artifact checks, build and three-platform workflows pass without weakening
  existing gates.

## Assumptions

- A separate isolated process satisfies the prompt's independent implementation boundary;
  another programming language is not required when the process has no access to the
  OpenARDP package or third-party libraries.
- The existing evidence contract and fixture family `0.1.0` remain authoritative inputs.
- Fixed synthetic text and tabular inputs are sufficient to falsify or narrowly support
  provider neutrality without pretending to measure production parser quality.
- Page geometry for the alternate tabular fixture is an explicitly declared deterministic
  provider view, not inferred visual truth.
- A passing internal spike is one independent-implementation data point but is not
  external-use evidence and does not satisfy stabilization governance.
