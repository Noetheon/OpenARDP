# Feature Specification: Domain Models and Interchange Schemas

**Feature Branch**: `codex/f002-domain-models-schemas`

**Created**: 2026-07-22

**Status**: Locally converged — remote validation pending

**Input**: User description: "Implement F002 completely, deeply, sustainably and according to best practice. Define the canonical OpenARDP domain objects and public JSON contracts so independently implemented components can exchange manifests, blocks, derivations, relations and context bundles deterministically."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Exchange trustworthy domain records (Priority: P1)

As an OpenARDP component author, I can create or consume a manifest, block, derivation, relation or context bundle through one canonical contract, so components agree on identity, provenance, trust and required content without depending on one another's implementation.

**Why this priority**: Every later ingestion, storage, retrieval and context feature depends on these records. Ambiguous or weak contracts here would spread incompatible data throughout the platform.

**Independent Test**: Validate one golden record of each public type, round-trip it through the canonical model contract, and validate the serialized result against the corresponding public schema without persistence, parsing, retrieval or network access.

**Acceptance Scenarios**:

1. **Given** valid golden records for all five public types, **When** a consumer validates and round-trips each record, **Then** every required field, identifier, provenance link, trust label and extension value is preserved and the result remains schema-valid.
2. **Given** a record with an unknown top-level field, malformed identifier, non-UTC timestamp, missing content or inconsistent source identity, **When** it is validated, **Then** validation fails with a field-specific explanation and does not silently coerce the record into validity.
3. **Given** an otherwise valid record with unfamiliar JSON-valued properties under `extensions`, **When** it is validated and round-tripped, **Then** those properties are preserved without granting them authority over core behavior.
4. **Given** document-derived content whose trust metadata permits instruction execution, **When** it is validated, **Then** the record is rejected because document content is data and cannot authorize tools.

---

### User Story 2 - Reproduce content identities (Priority: P2)

As a component author, I can serialize an identity payload canonically and compute its SHA-256 identity, so equivalent records converge on the same identifier regardless of process, object construction order or supported operating system.

**Why this priority**: Stable content identity enables safe reuse and later content-addressed storage. It must be established before persistence makes identifiers durable.

**Independent Test**: Compute canonical bytes and identities repeatedly in isolated processes from semantically identical payloads with permuted key order, then compare the exact bytes and digest strings.

**Acceptance Scenarios**:

1. **Given** semantically identical supported JSON values whose object keys were inserted in different orders, **When** canonical bytes and identities are produced in separate processes, **Then** the byte sequences and `sha256:` identifiers are identical.
2. **Given** a change that remains semantically distinct under the documented canonicalization rules, **When** its identity is produced, **Then** the result differs from the original identity; equivalent numeric representations are allowed to converge exactly as the canonicalization standard defines.
3. **Given** a non-finite number, unsupported runtime value or malformed precomputed digest, **When** canonicalization or validation is attempted, **Then** the operation fails explicitly rather than emitting unstable or implementation-specific output.
4. **Given** a Unicode string, **When** it is canonicalized, **Then** its exact code-point sequence is preserved; canonicalization does not silently apply textual normalization.

---

### User Story 3 - Evolve and audit interchange contracts (Priority: P3)

As a contract maintainer, I can identify the contract and algorithm version used by a record, regenerate reviewed schemas deterministically and reject incompatible major versions, so schema evolution is explicit and testable.

**Why this priority**: Long-lived packages and independently released components need a predictable compatibility boundary before any persisted data exists.

**Independent Test**: Regenerate every public schema, compare it byte-for-byte with the reviewed files, validate all supported-version fixtures and prove that malformed or unsupported-major versions are rejected with actionable errors.

**Acceptance Scenarios**:

1. **Given** a record using the explicitly supported `0.1.0` contract release, **When** it is read, **Then** its semantic version is accepted and preserved.
2. **Given** a syntactically invalid version or any unsupported major family, **When** a public record is read, **Then** validation fails clearly and reports the supported major family.
3. **Given** unchanged domain models and schema-generation rules, **When** schemas are regenerated repeatedly, **Then** every reviewed schema is byte-for-byte unchanged and declares JSON Schema 2020-12.
4. **Given** a proposed public field, invariant, compatibility or identity change, **When** it is reviewed, **Then** its schema, model, fixture, tests and changelog impact are traceable together.

### Edge Cases

- Object member order differs while list order remains semantically significant.
- Strings contain empty text, control characters, non-ASCII characters or canonically equivalent but code-point-distinct Unicode sequences.
- Numeric values include zero, negative zero, very large integers, fractional values or non-finite values.
- A digest uses uppercase hexadecimal, has the wrong length or omits the `sha256:` algorithm prefix.
- A timestamp is naive, uses a non-zero offset or falls on an RFC 3339 boundary value.
- A logical document identifier is a valid UUID but not the documented UUIDv7 form.
- A block has only null content fields, names itself as its parent or claims a source hash inconsistent with its version.
- A derivation has no inputs, duplicate inputs, inconsistent generator metadata or an identity that does not match its declared inputs and configuration.
- A relation contains an unsupported relation kind, malformed endpoint, invalid confidence value or a cross-version link without both endpoint versions.
- A context bundle contains duplicate source versions, an item not pinned to an exact version, a budget whose estimated use exceeds its limit, or an item with neither inline content nor an artifact handle.
- Extension data recursively contains a non-JSON value or attempts to replace a core field.
- A future minor or patch release is not installed in the reader, while an unsupported major version resembles an otherwise valid record.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST define canonical public contracts for Document Manifest, Content Block, Derivation Record, Relation and Context Bundle.
- **FR-002**: Every independently serialized public record MUST identify its semantic contract version and MUST reject malformed versions and unsupported major families.
- **FR-003**: A Document Manifest MUST identify one logical document, one exact source-byte version, one representation revision, the source facts, processing provenance, lifecycle state and creation time.
- **FR-004**: A manifest's source SHA-256 MUST be identical to the digest encoded by its source version identifier.
- **FR-005**: A Content Block MUST identify its logical document and exact source version, contain at least one non-null content representation, retain its structural position and source locator, carry a canonical content hash, and enforce trust metadata.
- **FR-006**: A Derivation Record MUST identify its output artifact, direct input identities, generating component and version, configuration identity, creation time, lifecycle state and optional model, prompt and quality metadata.
- **FR-007**: A Relation MUST represent a typed, directed link between two explicit domain references; every representation-dependent reference MUST pin its exact document, source version and representation, while content-addressed artifacts and namespaced external references MUST carry their own complete identity. Inferred links MUST retain algorithm and confidence provenance.
- **FR-008**: A Context Bundle MUST pin every selected item to an exact logical document and source version, record its query, evidence representation, budget, selection rationale, warnings and selection trace, and remain auditable without consulting implicit process state.
- **FR-009**: All content-bearing records MUST classify trust zone, role, integrity and sensitivity, and MUST enforce `instruction_execution_allowed=false`.
- **FR-010**: Unknown properties MUST be rejected at every core record boundary except inside an explicit `extensions` object.
- **FR-011**: Extension values MUST be valid JSON values, MUST round-trip unchanged and MUST NOT override, weaken or reinterpret core fields or invariants.
- **FR-012**: Required identifiers, non-negative lengths and order values, uniqueness constraints, referential self-conflicts and bounded values MUST be validated rather than silently normalized.
- **FR-013**: All timestamps MUST represent UTC instants and serialize as RFC 3339 strings; naive or non-UTC instants MUST be rejected.
- **FR-014**: Canonical serialization MUST produce one documented UTF-8 byte representation for every supported JSON value, independent of mapping insertion order and process execution.
- **FR-015**: Canonical serialization MUST preserve exact string code points and list order, reject non-finite numbers and unsupported values, and document its numeric and escaping rules.
- **FR-016**: Content identities MUST use SHA-256, a lowercase `sha256:` prefix and a separately documented algorithm-version identifier; Python's randomized `hash()` MUST never participate.
- **FR-017**: Identity-bearing records whose digest can be recomputed from their declared fields MUST reject inconsistent precomputed identifiers.
- **FR-018**: Each public record MUST have a reviewed JSON Schema 2020-12 contract with explicit identifier and semantic version metadata.
- **FR-019**: Public model validation and public schema validation MUST agree for every schema-expressible golden valid and invalid fixture covered by this feature.
- **FR-020**: Reviewed public schemas MUST be reproducibly generated or verified from one documented contract source so unreviewed model/schema drift fails an automated test.
- **FR-021**: Golden fixtures MUST cover every public contract, supported compatibility family, security invariant and persisted identity behavior introduced by this feature.
- **FR-022**: Invalid fixtures MUST cover malformed hashes and UUIDs, incompatible schema versions, unexpected properties, unsafe trust flags, missing content, non-UTC timestamps, non-JSON extensions, identity mismatches and cross-version ambiguity.
- **FR-023**: Tests MUST be deterministic, use only synthetic or redistributable fixtures and perform no network access.
- **FR-024**: Every public callable and model MUST be typed and documented, and domain code MUST remain pure with no filesystem, database, network, parser, service or interface dependency.
- **FR-025**: The feature MUST NOT implement persistence, document parsing, normalization workflows, retrieval, context selection behavior, a CLI or provider integration.
- **FR-026**: Every public contract change MUST update or explicitly confirm the affected model, schema, fixtures, compatibility declaration, tests and changelog entry.
- **FR-027**: Every invariant MUST be classified as schema-expressible, record-semantic or aggregate-semantic. F002 MUST document the enforcement owner for all three classes and MUST test every schema-expressible and record-semantic rule introduced here; aggregate-semantic rules owned by later bounded features MUST be traceable to that owner rather than prematurely implemented or misrepresented as standard-schema enforcement.

### Key Entities

- **Document Manifest**: The top-level description of one immutable source version and one normalized representation revision of a logical document.
- **Content Block**: A canonical, source-backed unit of document content with structure, provenance, identity and enforced trust classification.
- **Derivation Record**: The reproducibility and lifecycle record for a disposable artifact created from explicit input identities.
- **Relation**: A directed semantic or structural edge between typed, version-pinned domain references.
- **Context Bundle**: An immutable, auditable collection of selected evidence representations, exact source versions, budget accounting and selection trace.
- **Trust Classification**: Shared security metadata that distinguishes data from authority and describes integrity and sensitivity.
- **Source Locator**: Shared provenance metadata identifying the precise source location and extraction method without granting filesystem access.
- **Content Identity**: A versioned SHA-256 identifier over documented canonical bytes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One golden fixture for each of the five public record types validates successfully through both the canonical model and its JSON Schema and completes a lossless semantic round-trip.
- **SC-002**: Canonical bytes and SHA-256 identities remain identical across at least 20 fresh process executions, permuted mapping construction order and the Linux, macOS and Windows quality matrix.
- **SC-003**: A mutation that remains semantically distinct after canonicalization changes the relevant identity, while an insertion-order-only mutation changes neither canonical bytes nor identity; standardized equivalent numeric representations produce the same bytes and identity.
- **SC-004**: One hundred percent of the negative-fixture classes named in FR-022 are rejected at every validation layer capable of expressing that invariant, with each model-only or aggregate-only rejection explicitly classified and tested rather than misrepresented as a standard-schema rule.
- **SC-005**: All five public schemas validate as JSON Schema 2020-12 and regenerate or verify byte-for-byte without repository drift on two consecutive runs.
- **SC-006**: Every explicitly supported-version fixture is accepted and every malformed, uninstalled or unsupported-major fixture is rejected with an error that identifies the failing version field and supported releases or major family.
- **SC-007**: Automated traceability shows every FR-001 public record has a model, schema, valid fixture, invalid coverage and round-trip test, with no uncovered public contract.
- **SC-008**: The complete repository passes Ruff, formatting, strict mypy and pytest with branch coverage at or above the repository threshold and with network access disabled.
- **SC-009**: The delivered source tree introduces zero persistence, parser, retrieval, CLI, provider or network implementation modules.

## Assumptions

- The checked-in `0.1.0` schema release remains the current pre-stable interchange contract; this feature makes it executable and internally consistent without claiming compatibility with unshipped blueprint drafts.
- Readers accept only explicitly installed schema releases. Strict core objects reject unknown direct fields; forward-compatible experimental data belongs under `extensions`. A future minor release may add optional core fields, but an older reader is not required to accept that uninstalled schema.
- Removing fields, weakening invariants, changing identity inputs or changing canonicalization requires explicit compatibility and migration review under project governance.
- UUIDv7 generation belongs to later registration behavior; this feature validates documented identifiers and uses synthetic fixed values in fixtures.
- Canonicalization operates on supported JSON values. Format-specific text normalization belongs to later normalization work and is not performed implicitly here.
- Context selection, derivation execution and relation inference remain later use cases; F002 validates their records but does not perform those operations.
- Public schema files are committed review artifacts and may be consumed independently of the Python package.
- No external service, cloud call, database or original document is required to demonstrate this feature.
