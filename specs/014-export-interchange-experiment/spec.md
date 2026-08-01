# Feature Specification: Export and Interchange Experiment

**Feature Branch**: `codex/f014-export-interchange-experiment`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Authoritative Feature 014 prompt
`spec-kit/feature-prompts/014-export-interchange-experiment.md` (SHA-256
`a04a8f8c74e6b15073fbbe41e0fbed4e9fb5081eb78919b702899dc47bad98bd`) plus the
request to complete the remaining project sequentially with best-practice,
long-lived and sustainable implementation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Decide the Interchange Boundary from Evidence (Priority: P1)

As a project maintainer, I can compare RO-Crate, OCFL, BagIt and a minimal
project archive against the same concrete OpenARDP exchange needs and receive
an auditable decision that reuses an existing standard where it fits and does
not claim a universal OpenARDP format.

**Why this priority**: The constitution forbids inventing a project-owned
abstraction before prior art is evaluated. Every later export/import behavior
depends on a narrow, evidence-backed profile decision.

**Independent Test**: Apply the published criteria and synthetic vectors to
all four candidates and verify that the recorded decision identifies exact
support, required profiling, gaps, security consequences and rejected
alternatives without relying on implementation preference.

**Acceptance Scenarios**:

1. **Given** the four candidates and the same exchange scenarios, **When** the
   evaluation is run, **Then** every candidate is scored against integrity,
   completeness, semantic metadata, source references, extension policy,
   streaming, security, interoperability and implementation cost with cited
   evidence.
2. **Given** an existing standard that satisfies the transport/integrity
   boundary with a narrow profile, **When** the decision is recorded, **Then**
   OpenARDP adopts that profile instead of presenting a new universal format.
3. **Given** no candidate that safely satisfies a required exchange need,
   **When** the evidence is reviewed, **Then** a “no custom format” or
   research-only conclusion is accepted and unsupported runtime behavior is
   not shipped.
4. **Given** the selected outcome, **When** a maintainer reviews it, **Then**
   the independent export-profile version, stability, migration/reset path and
   residual interoperability limits are explicit.

---

### User Story 2 - Export a Complete Permitted Evidence Package (Priority: P1)

As a local operator, I can export an explicitly selected, internally
consistent evidence scope into the selected experimental interchange profile
without modifying the workspace or leaking local paths, secrets or assets that
are not permitted for redistribution.

**Why this priority**: A format evaluation is useful only if it proves that
real OpenARDP evidence and provenance can be exchanged faithfully and safely.

**Independent Test**: Populate a synthetic workspace with source versions,
native artifacts, projections, derivations and trust labels under every source
and native-asset disposition; export one exact scope twice and verify
completeness, integrity, policy enforcement, deterministic ordering and no
workspace mutation.

**Acceptance Scenarios**:

1. **Given** a healthy exact source-version scope and an explicit source/native
   asset policy, **When** export is requested, **Then** the package records all
   required contract/profile versions, identities, trust classifications,
   derivation relationships and integrity entries.
2. **Given** source bytes or provider-native assets explicitly permitted for
   redistribution, **When** export is requested with inclusion enabled,
   **Then** those exact bytes are included and independently hash-verifiable.
3. **Given** bytes that are not licensed, not permitted or intentionally kept
   local, **When** export is requested, **Then** the package records a
   non-secret opaque reference or omission reason and never includes the bytes.
4. **Given** local filenames, absolute paths, credentials, tokens, logs,
   transient jobs, staging residue and disposable indexes, **When** export is
   inspected, **Then** none appear in package paths, records or diagnostics.
5. **Given** unchanged inputs and policy, **When** the same semantic export is
   produced repeatedly, **Then** ordered records and package identity are
   identical apart from explicitly non-identifying report metadata.

---

### User Story 3 - Verify Before Import Publication (Priority: P1)

As a receiving operator, I can inspect and import a supported package only
after its complete structure, versions, policy and bytes verify within explicit
resource bounds, with no partial records or files becoming visible on failure.

**Why this priority**: Imported archives and records are attacker-controlled.
Pre-publication verification is the boundary that protects original evidence,
the catalog and local storage.

**Independent Test**: Import valid packages and one synthetic invalid vector
for every structure, path, size, count, version, checksum, identity,
relationship and collision rule; prove valid publication is complete and every
invalid case leaves the destination byte-for-byte unchanged.

**Acceptance Scenarios**:

1. **Given** a complete supported package within configured bounds, **When**
   verification and import are requested, **Then** every package and record
   digest is checked before one complete imported scope is published.
2. **Given** a missing, extra, duplicate, corrupt, truncated or conflicting
   entry, **When** import is attempted, **Then** the package is rejected before
   any authoritative fact or managed object becomes visible.
3. **Given** traversal, absolute, reserved, linked, device, case-colliding or
   ambiguous normalized paths, **When** import is attempted, **Then** the
   package is rejected without following or creating the unsafe entry.
4. **Given** expansion, file-count, per-file, total-size, path-depth or record
   limits are exceeded, **When** import is attempted, **Then** processing stops
   with a bounded body-free error and cleans only operation-owned staging.
5. **Given** a valid package whose deterministic import destination already
   contains the same completely verified package, **When** import is requested,
   **Then** it converges without duplication; if the same claimed identity maps
   to different bytes anywhere in the package, the complete import fails closed.

---

### User Story 4 - Preserve Compatibility Without Trust Elevation (Priority: P2)

As a receiving operator, I can understand which package/profile and record
versions are supported, how declared extensions are handled and why imported
content remains untrusted even when all integrity checks pass.

**Why this priority**: Integrity proves byte equality, not authenticity, truth,
license or permission. Explicit compatibility and extension rules prevent
silent semantic loss and future lock-in.

**Independent Test**: Exercise the exact supported profile, unsupported major
and uninstalled minor versions, declared preserve/reject extension modes and
malicious instruction-like document content; verify deterministic outcomes and
unchanged trust classification.

**Acceptance Scenarios**:

1. **Given** an unsupported export-profile or record-contract version, **When**
   verification/import is requested, **Then** it is rejected distinctly from a
   malformed or integrity-invalid package.
2. **Given** extensions under a declared preserve policy, **When** import and
   re-export occur, **Then** JSON-only extension data is preserved exactly
   without affecting identity, policy or execution; undeclared fields remain
   rejected.
3. **Given** extensions under a declared reject policy, **When** any extension
   is present, **Then** import fails before publication with the exact policy
   reason.
4. **Given** cryptographically valid imported document text or model-derived
   content, **When** it is queried or re-exported, **Then** it remains untrusted
   data and cannot authorize tools, network access, license changes or trust
   elevation.
5. **Given** source and native-asset licensing/disposition facts, **When** a
   package is imported, **Then** they are preserved as sender assertions and
   never treated as receiver-verified legal permission.

---

### User Story 5 - Reproduce the Experiment Across Platforms (Priority: P2)

As a maintainer or independent evaluator, I can run redistributable test vectors
and obtain the same decision-relevant export, verification and import outcomes
on Linux, macOS and Windows without network access.

**Why this priority**: Interoperability and security claims require repeatable
evidence beyond one machine or implementation path.

**Independent Test**: Run the committed positive and negative package corpus on
all supported platforms, regenerate expected artifacts, and verify zero drift
in identities, classification and decision evidence.

**Acceptance Scenarios**:

1. **Given** the committed valid/invalid vector manifest, **When** validation is
   run offline on each supported platform, **Then** every vector has the same
   expected outcome and stable error category.
2. **Given** a generated golden package, **When** regeneration is run from the
   same synthetic facts, **Then** all normative bytes and identities match or a
   drift check fails.
3. **Given** the experiment decision, **When** its evidence is reviewed, **Then**
   limitations, non-goals and any standard/profile deviations are visible and
   no result is described as universal conformance.

### Edge Cases

- The selected scope changes while export inventories catalog facts or streams
  object bytes.
- The same object is required by multiple record families or appears under
  multiple logical roles.
- A source is includable while one provider-native derivative is not, or vice
  versa.
- Permission is absent, unknown, contradictory, revoked during export or stated
  only by untrusted imported metadata.
- A package contains zero payload entries, an empty source, very long paths,
  non-ASCII names, decomposed Unicode, mixed separators or platform-reserved
  names.
- A package contains duplicate archive members, nested archives, sparse files,
  links, junction-like entries, device files, encrypted members or data
  descriptors whose reported and actual sizes disagree.
- Multiple manifests disagree, list themselves, omit tag metadata, use weak or
  unknown algorithms, or contain duplicate/case-variant digests.
- An archive's compressed size is small but expanded bytes, entry count,
  compression ratio or nesting exceed policy.
- Records are structurally valid but reference missing, extra, cyclic, stale or
  cross-scope identities.
- The import destination already contains the identical verified package, a
  conflicting package, foreign entries or insufficient capacity reserve.
- Export/import is interrupted before manifest publication, during streaming,
  after staging verification or during catalog publication.
- Two processes export the same scope or import the same package concurrently.
- A package declares remote retrieval, executable content, signatures or
  authenticity assertions that the selected experimental profile does not
  support.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The feature MUST publish an evidence matrix and accepted decision
  record comparing RO-Crate, OCFL, BagIt and a minimal project archive against
  identical documented exchange and threat scenarios.
- **FR-002**: Evaluation criteria MUST include existing-standard fit, package
  completeness, byte integrity, semantic metadata, independent versioning,
  source/reference policy, licensing, extension behavior, streamability,
  deterministic generation, safe import, implementation/supply-chain cost and
  independent-tool interoperability.
- **FR-003**: Every candidate conclusion MUST cite authoritative specification
  evidence, distinguish standard behavior from a proposed OpenARDP profile and
  record material gaps and residual risks.
- **FR-004**: The decision MUST prefer an existing maintained standard or a
  narrow profile where it satisfies requirements. A custom archive requires an
  accepted rationale for every unmet prior-art alternative; a “no custom
  format” conclusion MUST remain valid.
- **FR-005**: Any delivered profile MUST be labelled experimental, have its own
  semantic version independent of application, workspace, contract and provider
  versions, and MUST NOT use or imply a universal `.ardp` file type.
- **FR-006**: Export MUST require an explicit exact source-version/evidence scope,
  destination and source/native-asset disposition policy; defaults MUST not
  redistribute original or provider-native bytes without affirmative permission.
- **FR-007**: Export MUST establish one stable catalog/root snapshot, enumerate
  every required authoritative and derived dependency, verify exact bytes while
  streaming and fail if the scope changes before publication.
- **FR-008**: A package MUST record its export-profile version, every contained
  public contract/provider profile version, canonical identity algorithm,
  creation policy, selected scope and declared extension policy.
- **FR-009**: A package MUST contain a complete deterministic integrity inventory
  covering every payload and normative metadata entry with relative portable
  path, exact byte length and SHA-256 digest.
- **FR-010**: A package MUST represent source and provider-native asset
  disposition separately as included, externally referenced or omitted, with a
  closed reason and sender-asserted permission/license metadata where supplied.
- **FR-011**: Included bytes MUST retain their existing content identity.
  External references MUST be opaque data, MUST NOT contain credentials and MUST
  never trigger network retrieval during export, verification or import.
- **FR-012**: A package MUST include the selected scope's portable source/version,
  native/evidence projection, derivation and trust facts needed to interpret
  included objects without copying runtime database rows or provider classes.
- **FR-013**: Export MUST exclude secrets, credentials, absolute paths, local
  usernames, unapproved original/native bytes, diagnostic bodies, transient
  jobs, maintenance state, staging residue, caches and disposable indexes.
- **FR-014**: Export paths and record ordering MUST be canonical and portable
  across Linux, macOS and Windows; conflicting case, Unicode normalization,
  separator, reserved-name and control-character representations MUST be
  rejected rather than renamed silently.
- **FR-015**: Repeating export against identical semantic inputs and policy MUST
  produce the same normative package identity and entry bytes. Report timestamps
  MAY differ only outside identity-bearing content.
- **FR-016**: Export MUST write only to a fresh disjoint local destination and
  MUST publish completion atomically after all package bytes and manifests pass
  self-verification; failure MUST not mutate the source workspace.
- **FR-017**: Verification MUST parse package structure and bounded metadata
  without extracting to an authoritative destination, then verify completeness,
  versions, paths, entry types, counts, lengths, digests and cross-record
  semantics before import publication.
- **FR-018**: Import MUST use explicit configurable limits for archive bytes,
  expanded bytes, compression ratio, entry count, individual entry bytes,
  metadata bytes, path length/depth and record relationships; defaults, units,
  allowed ranges and failure behavior MUST be documented.
- **FR-019**: Import MUST reject absolute/traversing paths, links, hard-link
  aliases, devices, duplicate members, ambiguous normalized/case-colliding
  paths, nested archives, encrypted entries and entries not declared by the
  selected profile.
- **FR-020**: Import MUST reject missing, extra, duplicate, truncated, corrupt or
  digest-conflicting content and MUST distinguish malformed, unsupported,
  policy-rejected, resource-exhausted and integrity-invalid results without
  exposing package bodies or local paths.
- **FR-021**: Import MUST publish one completely verified, immutable package
  snapshot at a fresh disjoint destination or none. Interrupted or concurrent
  duplicate imports MUST converge from the verified package identity and MUST
  never guess authority from staging filenames.
- **FR-022**: Import MUST reject any duplicate or conflicting claimed object
  identity inside the package before publication. Repeating import of the exact
  same package to the same destination MAY converge only after complete
  re-verification; merging into an existing workspace catalog is not part of
  this experiment.
- **FR-023**: Import MUST reject unsupported profile and public-contract versions
  distinctly. The initial experimental reader MUST accept only explicitly
  installed versions and MUST never infer them from application/workspace versions.
- **FR-024**: Closed record objects MUST reject unknown fields. JSON-only data
  under a declared `extensions` container MUST either be preserved exactly or
  cause whole-package rejection according to the package's declared supported
  extension policy; extensions MUST NOT alter core identity, permission or trust.
- **FR-025**: All imported document, metadata, references and extensions MUST
  remain untrusted data. Integrity verification MUST NOT be described or treated
  as proof of authenticity, truth, ownership, license or execution authority.
- **FR-026**: Import MUST not contact referenced locations, execute package
  content, load plugins, resolve remote contexts or enable any cloud/provider
  integration.
- **FR-027**: The feature MUST provide synthetic or redistributable valid and
  invalid vectors for every normative export/import rule, including path
  traversal, duplicate/collision, expansion/count/size, checksum, version,
  extension, relationship, license/disposition and trust cases.
- **FR-028**: At least one package validator MUST run independently of runtime
  adapters and the complete vector corpus MUST run offline with stable outcomes
  on Linux, macOS and Windows.
- **FR-029**: Golden vector generation MUST be deterministic, reviewable and
  guarded by a drift check; generated artifacts MUST not contain real or
  confidential document data.
- **FR-030**: Operator-facing export, verify and import results MUST be bounded,
  machine-readable and body-free by default, reporting stable identifiers,
  counts, bytes, profile versions and sanitized error categories only.
- **FR-031**: No MCP method, watcher job, startup path, retention operation or
  document content MAY initiate export/import. These remain explicit trusted
  operator actions outside the read-only MCP surface.
- **FR-032**: The feature MUST update authoritative documentation, security
  boundaries, compatibility policy, conformance guidance and changelog to state
  exactly what was selected, implemented, unsupported and measured.

### Non-Goals and Compatibility Impact

- **Non-goal**: Declare OpenARDP, its schemas or an export suffix to be a
  universal standard, or claim complete semantic equivalence with another
  parser/provider.
- **Non-goal**: Provide long-term repository versioning, preservation policy,
  remote synchronization, registries, discovery, cloud transfer or automatic
  reference fetching.
- **Non-goal**: Add signatures, attestations, authenticity certification,
  encryption, DRM, secure erasure or legal/license verification.
- **Non-goal**: Export an entire live workspace database, internal operation/job
  history, indexes, caches, embeddings or unknown provider-native bytes without
  explicit permission.
- **Non-goal**: Add write-capable MCP, import arbitrary workspace backups, or
  replace F013 backup/restore and migration semantics.
- **Non-goal**: Merge portable records or objects into an existing live
  workspace catalog/CAS. The experiment publishes a separately inspectable
  verified snapshot; a future feature may design workspace merge semantics from
  interoperability evidence.
- **Compatibility impact**: Additive experimental export-profile surface and
  operator commands only if the evidence decision supports implementation.
  Application remains `0.0.1`; current workspace/catalog revision and existing
  public contract/provider-profile versions remain unchanged. The new export
  profile begins independently at `0.1.0`; unsupported versions fail closed and
  future breaking changes require migration/reset guidance, fixtures, changelog
  and an ADR.

### Key Entities

- **Interchange Decision**: The criteria, candidate evidence, selected outcome,
  deviations, residual risks and conditions for revisiting the decision.
- **Export Profile**: An independently versioned experimental agreement over
  required package structure, algorithms, metadata, limits and compatibility.
- **Export Scope**: The exact source version and transitive portable evidence,
  derivation and object dependencies selected by a trusted operator.
- **Asset Disposition**: The include/reference/omit decision and closed reason for
  each source or provider-native asset, plus optional sender-asserted permission
  and license facts.
- **Package Inventory**: The canonical complete set of normative package paths,
  byte lengths and SHA-256 digests plus the identity of its profile and scope.
- **Extension Policy**: The declared reject-or-preserve behavior for bounded
  JSON-only extension containers under explicitly supported versions.
- **Import Plan**: A verified, bounded, immutable summary of all objects and
  portable facts that would be published, produced before any authoritative
  mutation.
- **Import Result**: The terminal complete/rejected outcome with stable body-free
  counts, identities and error categories.
- **Conformance Vector**: A synthetic package plus expected profile, validation,
  import and security outcome independent of the runtime adapter.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: One accepted ADR evaluates all four candidates against 100% of the
  published criteria and traces every selection/rejection claim to an
  authoritative source or committed reproducible vector.
- **SC-002**: Two exports of each of at least three representative synthetic
  scopes produce identical normative package identities and bytes on Linux,
  macOS and Windows.
- **SC-003**: Every supported exported scope can be verified and imported into a
  clean destination with 100% of included objects, portable records,
  relationships, versions, dispositions and trust labels preserved.
- **SC-004**: Repeating a valid import of the same package converges to one
  immutable snapshot; every in-package identity/digest-conflict vector publishes
  zero entries.
- **SC-005**: 100% of the committed traversal, link, duplicate, collision,
  expansion, count, size, corruption, version, extension and cross-record attack
  vectors are rejected before authoritative publication on all three supported
  platforms.
- **SC-006**: Exported packages and all operator results contain zero absolute
  paths, credentials, local usernames, document bodies outside explicitly
  permitted payloads, transient runtime records or undisclosed assets across the
  complete synthetic corpus.
- **SC-007**: Import resource limits stop processing no later than the first
  violating entry/relationship and leave the target's pre-import authoritative
  bytes and facts unchanged in 100% of boundary and interruption tests.
- **SC-008**: The independent validator classifies every committed valid and
  invalid vector identically to the runtime import preflight without using a
  workspace, parser, model provider or network access.
- **SC-009**: Repeated and twenty-way concurrent export/import requests for the
  same identity converge to one deterministic package/import outcome; conflicting
  requests fail without partial publication.
- **SC-010**: Documentation explicitly identifies the selected standard/profile,
  experimental version, unsupported capabilities and distinction between
  integrity, authenticity, truth, license and trust, with no universal-format
  claim.

## Assumptions

- Feature 013 is merged, converged and supplies the current workspace integrity,
  capacity, atomic filesystem and explicit recovery foundations.
- Exchange is a trusted operator action over a local healthy workspace and local
  destination; packages themselves and all contained content are untrusted.
- The experiment targets a self-contained, finite exchange snapshot. Remote
  references may be recorded as inert data but are never fetched by this feature.
- SHA-256 remains the required content and package inventory algorithm even if an
  adopted base standard permits additional or weaker algorithms.
- Source/native inclusion requires affirmative operator policy backed by known
  redistribution permission; unknown permission defaults to reference or omission.
- The initial profile accepts one exact experimental release. Broad minor-version
  negotiation and format migration are deferred until real interoperability
  evidence exists.
- The standard library and current locked dependencies are preferred. Any new
  dependency requires explicit maintenance, license, security and supply-chain
  evidence during planning.
