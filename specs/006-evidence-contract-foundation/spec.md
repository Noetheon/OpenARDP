# Feature Specification: Evidence Contract Foundation

**Feature Branch**: `codex/f006-evidence-contract-foundation`

**Created**: 2026-07-26

**Status**: Converged locally; remote verification pending

**Input**: Define the smallest experimental provider-neutral native-representation,
evidence-reference, evidence-projection, and trust contracts before any rich-parser
adapter is implemented.

## User Scenarios & Testing

### User Story 1 - Exchange Source-Bound Evidence Safely (Priority: P1)

As an adapter or integration author, I can produce and validate a minimal evidence
reference whose identity and anchor are bound to one exact source version and one
provider-native representation.

**Why this priority**: Evidence that can drift to a different source revision or be
interpreted without its native representation cannot support trustworthy retrieval,
citations, or later conformance work.

**Independent Test**: A standalone consumer can validate reviewed text-span,
page-region, table-cell, and opaque provider-pointer examples without installing or
executing a parser, while stale versions, invalid geometry, and malformed pointers are
rejected.

**Acceptance Scenarios**:

1. **Given** two logically identical evidence references with different JSON property
   order, **When** their identities are calculated, **Then** both produce the same
   reviewed canonical bytes and SHA-256 identifier.
2. **Given** a reference whose source version differs from the retained native
   representation, **When** the records are validated together, **Then** validation
   fails without rewriting either record.
3. **Given** a normalized page region, **When** any coordinate is non-finite, negative,
   zero-sized, or extends beyond the declared page bounds, **Then** the record is
   rejected.
4. **Given** an opaque provider pointer, **When** its profile scope, format identifier,
   or bounded pointer value is missing or malformed, **Then** the record is rejected
   without interpreting the pointer as a path, URL, or command.

---

### User Story 2 - Preserve Native Fidelity Without a Second Full IR (Priority: P2)

As a rich-parser adapter author, I can register one complete immutable provider-native
artifact and emit only a thin provider-neutral projection needed for evidence identity,
navigation, retrieval, trust, and lifecycle.

**Why this priority**: The first rich adapter must not turn its provider-specific object
model into an accidental OpenARDP-wide document representation.

**Independent Test**: A reviewer can validate native-representation and projection
fixtures and prove that the neutral surface contains no parser node class, database row,
filesystem path, ranking score, or embedded complete document tree.

**Acceptance Scenarios**:

1. **Given** a complete provider-native artifact stored by content identity, **When** its
   native-representation record is validated, **Then** the record identifies exact source
   input, immutable artifact, generating component, provider profile, and creation time.
2. **Given** a thin evidence projection, **When** it is validated, **Then** it references
   source-bound evidence and content-addressed retrieval material without duplicating the
   provider's complete native model.
3. **Given** two provider profiles use different internal pointer syntax, **When** their
   evidence references are exchanged, **Then** each pointer remains opaque and explicitly
   profile-scoped, with no claim of cross-provider semantic equivalence.

---

### User Story 3 - Enforce Trust and Version Boundaries (Priority: P3)

As a security-conscious consumer, I can reject evidence that attempts to become more
trusted than its origin, authorize instruction execution, or masquerade as a supported
contract version.

**Why this priority**: Contract-level trust and version checks prevent silent privilege
escalation and ambiguous compatibility before higher-level interfaces consume evidence.

**Independent Test**: Reviewed valid and invalid trust/version fixtures pass through an
adapter-independent validator with deterministic diagnostics and no network access.

**Acceptance Scenarios**:

1. **Given** externally untrusted source evidence, **When** a classification labels it
   organization- or local-trusted, **Then** the classification is rejected.
2. **Given** any document-originated evidence, **When** instruction execution is enabled
   or its authority role is not data, **Then** the classification is rejected.
3. **Given** malformed, uninstalled, and unsupported-major contract versions, **When**
   each is validated, **Then** the three failure categories remain distinguishable.
4. **Given** an unknown direct field, **When** the record is validated, **Then** it is
   rejected; a valid namespaced JSON extension is preserved verbatim.

---

### User Story 4 - Reuse the Contracts Independently (Priority: P4)

As an independent implementer, I can use published schemas, conformance fixtures,
identity vectors, and standards-mapping guidance without depending on OpenARDP adapters
or treating W3C mappings as mandatory wire fields.

**Why this priority**: Provider neutrality and interoperability are hypotheses until a
second implementation can exercise an exact, bounded contract.

**Independent Test**: A clean validator invocation discovers the manifest of valid and
invalid fixtures, validates all four root schemas, verifies golden identities, and
completes offline without importing any adapter package.

**Acceptance Scenarios**:

1. **Given** the committed conformance fixture manifest, **When** the standalone validator
   runs, **Then** every valid fixture is accepted and every invalid fixture fails for its
   declared category.
2. **Given** the contract documentation, **When** an implementer maps records to W3C PROV
   or Web Annotation concepts, **Then** the guidance identifies reusable concepts and
   known mismatches without adding mandatory JSON-LD or external-standard fields.
3. **Given** the Feature 005 public schemas, **When** Feature 006 schemas are added and all
   prior fixtures are revalidated, **Then** the earlier schema bytes and behavior remain
   unchanged.

### Edge Cases

- Equivalent JSON values use different object insertion order or JCS-equivalent number
  spellings: canonical bytes and identities converge.
- Unicode text is canonically serialized without normalization: NFC and NFD remain
  distinct evidence when their source bytes or pointer values differ.
- A text span is empty, reversed, or outside a declared text extent: it is rejected.
- A table cell uses negative coordinates, zero spans, or arithmetic that exceeds the safe
  interoperable integer range: it is rejected.
- A page number is zero or a normalized rectangle reaches outside `[0, 1]`: it is
  rejected.
- An opaque pointer contains control characters, exceeds its declared bound, or lacks a
  provider-profile version: it is rejected as malformed but never dereferenced.
- A projection embeds a reference for another source or native representation: it is
  rejected as stale/mismatched.
- A projection's declared identifier no longer matches its identity-significant fields:
  it is rejected rather than silently recomputed.
- Extension data contains an unnamespaced key, duplicate JSON object name, unsafe integer,
  non-finite number, or non-standard constant: it is rejected.
- Trust is downgraded conservatively: this is allowed; trust promotion or promotion out
  of `model_derived` is rejected.
- A newer experimental minor release is syntactically valid but not installed: it is
  rejected distinctly rather than accepted optimistically.
- A contract document or fixture contains natural-language instructions: the content is
  validation data only and cannot initiate parser, filesystem, network, or tool actions.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST publish additive experimental root contracts for
  `NativeRepresentation`, `EvidenceReference`, `EvidenceProjection`, and
  `TrustClassification`.
- **FR-002**: Every root contract MUST declare its own semantic `contract_version` and an
  `experimental` stability label independently of application, workspace,
  provider-profile, and export-profile versions.
- **FR-003**: Readers MUST reject malformed semantic versions, syntactically valid but
  uninstalled versions, and unsupported major versions as distinct failure categories.
- **FR-004**: Direct record fields MUST be closed; unknown data MUST be accepted only
  within an `extensions` object whose keys are absolute namespace identifiers and whose
  values are valid interoperable JSON.
- **FR-005**: Every persisted contract identity MUST use a documented versioned,
  purpose-specific RFC 8785 envelope and lowercase SHA-256 digest over an explicit
  allowlisted projection.
- **FR-006**: Identity projections MUST exclude timestamps, trust labels, lifecycle
  observations, and extensions unless a future ADR and migration explicitly changes an
  identity projection.
- **FR-007**: `NativeRepresentation` MUST identify the exact source version, immutable
  native artifact, provider and provider-profile versions, generating component and
  version, configuration identity, media type, byte length, and UTC creation time.
- **FR-008**: A native-representation identifier MUST change when any documented
  identity-significant source, provider recipe, profile, configuration, or native
  artifact identity changes.
- **FR-009**: `EvidenceReference` MUST bind exactly one anchor to one source version and
  one native-representation identifier and MUST verify its declared identifier.
- **FR-010**: The anchor union MUST support text spans, normalized page regions, table
  cells, and opaque provider pointers using an explicit discriminator and mutually
  exclusive fields.
- **FR-011**: Text anchors MUST use bounded half-open offsets with `end > start`; when a
  text extent is declared, the span MUST fit within it.
- **FR-012**: Page-region anchors MUST use one-based page numbers and a declared,
  fixed-point normalized top-left coordinate system; rectangles MUST have positive area
  and remain entirely within the page bounds without binary floating-point ambiguity.
- **FR-013**: Table-cell anchors MUST use zero-based row/column indices, positive spans,
  and one bounded, profile-scoped opaque pointer to the containing native table.
- **FR-014**: Opaque provider pointers MUST declare provider profile, independent
  provider-profile version, pointer format, and a bounded non-control string; validators
  MUST treat the pointer only as data.
- **FR-015**: `EvidenceProjection` MUST contain only source/native/reference identity,
  bounded navigation data, content-addressed retrieval handles, trust, and immutable
  generation/lifecycle facts; it MUST NOT reproduce a complete provider-native tree.
- **FR-016**: Every projection MUST validate that its embedded evidence reference belongs
  to the same source version and native representation and that its declared identifier
  matches the documented projection.
- **FR-017**: `TrustClassification` MUST keep document-originated content in role `data`,
  force instruction execution to false, record origin and effective trust zones,
  integrity and sensitivity, and reject effective trust promotion.
- **FR-018**: The trust policy MUST allow an explicit conservative downgrade, preserve
  `model_derived` as model-derived, and reject promotion from external, organization, or
  model-derived origins into a more authoritative zone.
- **FR-019**: The public validation API MUST validate raw JSON without duplicate object
  names, non-standard constants, unsafe integers, value echo in errors, network access,
  adapter imports, pointer dereferencing, or filesystem reach.
- **FR-020**: An adapter-independent command MUST validate the reviewed conformance
  manifest, all valid/invalid fixtures, cross-record source bindings, and golden
  canonical/digest vectors deterministically.
- **FR-021**: Conformance fixtures MUST be synthetic or redistributable and MUST cover all
  four roots, all anchor variants, version negotiation, extension behavior, stale source
  bindings, invalid geometry, malformed pointers, identifier drift, and trust
  escalation.
- **FR-022**: Every generated schema MUST use JSON Schema 2020-12, deterministic reviewed
  bytes, a stable identifier, explicit version/stability metadata, and drift checking.
- **FR-023**: W3C PROV and Web Annotation guidance MUST document mappings, non-mappings,
  and optional profiles without making JSON-LD, remote contexts, or external vocabulary
  fields mandatory in the wire contracts.
- **FR-024**: The contracts MUST NOT encode Docling classes, Python runtime types, SQLite
  rows, local filesystem paths, ranking scores, model prompts, or executable locators.
- **FR-025**: Feature 005 public schemas, fixtures, identifiers, and compatibility
  behavior MUST remain byte-for-byte and semantically unchanged; Feature 006 is an
  additive experimental contract family.
- **FR-026**: Public documentation, schema inventory, changelog, migration notes,
  implementation notes, and rollback instructions MUST describe the new contracts and
  their experimental compatibility boundary.
- **FR-027**: All public functions and validators MUST be typed and documented, and every
  contract behavior change MUST have an offline automated test.

### Non-Goals and Compatibility Impact

- **Non-goal**: Implement Docling, any rich-parser adapter, OCR, visual rendering, context
  compilation, MCP, search ranking, catalog persistence, export packaging, or an
  alternate parser.
- **Non-goal**: Define a complete provider-neutral document object model or claim semantic
  equivalence between provider-native pointers.
- **Non-goal**: Stabilize an interoperability standard, require JSON-LD, or claim W3C
  conformance.
- **Non-goal**: Change existing representation, block, derivation, relation, manifest, or
  context-bundle identity algorithms.
- **Compatibility impact**: Additive experimental contract family `0.1.0`; no application
  version requirement, no workspace migration, no provider-profile version assignment,
  and no export-profile change. The existing Feature 005/F002 public schema family remains
  unchanged. A later breaking experimental contract change requires changelog, fixtures,
  migration/reset guidance, and an ADR when identity or compatibility semantics change.

### Key Entities

- **Native Representation**: Immutable metadata for a complete provider-native artifact,
  bound to exact source bytes and a versioned provider recipe.
- **Evidence Reference**: Canonically identified source/native binding plus one validated
  anchor variant.
- **Text Span Anchor**: Half-open character interval within a declared provider text
  coordinate space.
- **Page Region Anchor**: Positive normalized rectangle on a one-based page in a declared
  top-left coordinate system.
- **Table Cell Anchor**: Zero-based cell coordinate and spans scoped to an opaque pointer
  for the containing native table.
- **Opaque Provider Pointer**: Bounded uninterpreted provider-profile data carrying its
  own format and profile version.
- **Evidence Projection**: Thin immutable navigation/retrieval record that cites an
  evidence reference and content-addressed material without duplicating a complete native
  representation.
- **Trust Classification**: Origin/effective trust boundary, data-only authority,
  integrity, sensitivity, and non-execution invariant.
- **Conformance Manifest**: Offline inventory of valid, invalid, cross-record, and identity
  vectors with expected outcomes.

## Success Criteria

### Measurable Outcomes

- **SC-001**: All four root contracts have deterministic JSON Schema 2020-12 files,
  reviewed valid/invalid fixtures, and raw-JSON model parity tests.
- **SC-002**: 100% of reviewed canonical/digest vectors reproduce byte-for-byte and
  identifier-for-identifier across repeated processes and supported CI operating
  systems.
- **SC-003**: The standalone validator accepts every declared valid fixture and rejects
  every declared invalid fixture for its expected category with zero adapter imports,
  network calls, pointer dereferences, or filesystem access outside the supplied fixture
  tree.
- **SC-004**: Automated negative tests reject every stale source/native binding, invalid
  text/table/page geometry, malformed opaque pointer, identifier mismatch, unsupported
  version, unknown direct field, unnamespaced extension, and trust-escalation case in the
  conformance manifest.
- **SC-005**: A repository diff proves zero byte changes to the five existing Feature 005
  public schemas and their canonical identity vectors.
- **SC-006**: A contract-surface audit finds zero Docling symbols, Python type names,
  SQLite concepts, filesystem paths, ranking fields, executable locators, or complete
  provider-native subtrees in the four new schemas.
- **SC-007**: The W3C mapping guide covers every root and anchor variant and labels every
  mapping as reusable, profile-specific, or deliberately unmapped without requiring
  network resolution.
- **SC-008**: Ruff, formatting, strict mypy, the complete network-blocked test suite,
  deterministic schema/conformance validation, distribution build, and Linux/macOS/Windows
  CI all pass without weakening prior gates.

## Assumptions

- Contract release `0.1.0` is experimental and readers accept only explicitly installed
  releases.
- Existing RFC 8785/JCS and strict raw-JSON facilities are reused through their narrow
  domain boundary; no second canonicalizer is introduced.
- SHA-256 artifact identifiers refer to immutable content-addressed bytes, not local
  paths or authorization capabilities.
- Page geometry uses integer parts-per-million in `[0, 1_000_000]` with origin at the
  top-left and axes increasing right/down; physical units, binary floating-point
  coordinates, and rotations are deferred.
- Text offsets are Unicode scalar/code-point offsets in a provider-declared text view;
  the contract does not claim equivalent offsets across providers.
- Opaque pointers are profile-scoped identifiers only. A consumer needs the corresponding
  native artifact and provider-profile knowledge to interpret them.
- A projection references existing content-addressed block or asset material rather than
  embedding a second complete document structure.
- No user clarification is required because the accepted ADRs, v3.1 feature prompt,
  constitution, and conservative compatibility policy define one bounded solution.
