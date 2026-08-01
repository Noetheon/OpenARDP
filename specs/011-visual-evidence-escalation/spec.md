# Feature Specification: Visual Evidence Escalation

**Feature Branch**: `codex/f011-visual-evidence-escalation`

**Created**: 2026-08-01

**Status**: Draft

**Input**: Retrieve exact page, image, table and deterministic crop evidence while
keeping OCR and captions optional, provider-neutral, local-first, provenance-rich and
explicitly untrusted. Visual artifacts are content-addressed, freshness-checked,
license/export constrained and bounded against hostile image/document inputs.

## Clarifications

### Session 2026-08-01

- Q: Does F011 create a complete provider-neutral page/layout model? -> A: No. It adds
  one thin experimental visual-evidence descriptor around existing F006 anchors,
  source/native identities, exact raster/crop objects and transforms. Complete
  provider-native structure remains in the retained native artifact.
- Q: What is the authoritative visual fact? -> A: Original source bytes remain
  authoritative. A rendered page and a crop are reproducible derived views with an
  exact source version, rendering/cropping recipe and digest. OCR and captions are
  further untrusted interpretations and can never replace the raster or original.
- Q: Which inputs receive a built-in rendering path? -> A: The initial concrete
  renderer is the optional, local PDF page path. Provider-neutral ports admit later
  Office or alternate renderers without changing the core descriptor. For a source or
  target without an installed safe renderer or resolvable region, retrieval fails
  honestly with a stable unavailable reason; it never fabricates a screenshot.
- Q: How are pictures and tables retrieved without duplicating the parser model? -> A:
  A caller requests an accepted F006 evidence projection. Page-region anchors crop the
  exact page. Provider/table pointers are resolved only inside the exact retained
  native JSON; a cell crop uses explicit cell geometry when present and otherwise may
  return the containing table region with a machine-readable granularity warning. No
  geometry is inferred from text or model output.
- Q: Does context compilation invoke an OCR/caption model? -> A: No. VISUAL compilation
  discovers current materialized visual artifacts and returns exact handles. When none
  satisfy the request it preserves `visual_evidence_required`. Materialization is an
  explicit bounded local operation, after which compilation can deterministically
  select the handle. OCR/caption derivations are separately explicit and disabled by
  default.
- Q: Can metadata embedded in a document grant export rights or change orientation? ->
  A: No. Document metadata and EXIF are untrusted data. Pixel orientation comes only
  from the versioned renderer contract; licensing/export policy comes from trusted
  out-of-band configuration and defaults conservatively to local-only with export
  denied when rights are unknown.
- Q: How are crop boundaries rounded? -> A: The F006 normalized top-left rectangle is
  mapped to the rendered display raster with integer floor for the inclusive left/top
  edges and integer ceiling for the exclusive right/bottom edges. No clamping or repair
  is permitted; every result must remain strictly in bounds with positive area. The
  descriptor records both coordinate spaces and the complete transform.
- Q: How is parser geometry aligned with the independently rendered PDF page? -> A:
  The service compares provider-native and rendered display aspect ratios after their
  declared rotations using integer fixed-point arithmetic. The canonical recipe permits
  at most 1,000 PPM (0.1%) relative aspect error; a larger disagreement fails with
  `page_geometry_mismatch` rather than applying an inferred stretch.
- Q: Does F011 add new MCP write tools or background jobs? -> A: No. It adds a local
  application/CLI materialization path and makes existing context compilation capable
  of selecting verified visual handles. F009 remains read-only, and F012 owns durable
  scheduling, leases and watcher automation.

## User Scenarios & Testing

### User Story 1 - Materialize Exact Visual Evidence (Priority: P1)

As a local operator or application service, I can request the visual evidence for one
accepted page, picture, table or table-cell projection and receive an immutable handle,
a bounded crop and enough provenance to reproduce and verify it.

**Why this priority**: Exact visual retrieval is the missing evidence layer needed to
answer layout, image and low-confidence extraction questions without inventing detail.

**Independent Test**: Ingest a synthetic PDF containing rotated pages, text, an image
and a table; request each accepted projection; verify raster/crop bytes, dimensions,
coordinate transforms, identities and descriptor replay across fresh processes.

**Acceptance Scenarios**:

1. **Given** a current accepted projection with an exact page-region anchor, **When**
   visual evidence is materialized, **Then** the returned crop contains precisely the
   deterministic display-pixel rectangle, and its descriptor binds the source,
   representation, reference, projection, page raster, crop object and recipe.
2. **Given** a full-page projection, rotated page or non-unit render scale, **When** it
   is materialized repeatedly, **Then** page orientation and scaling are explicit and
   the same semantic request under the same exact wheel-bound recipe converges on
   byte-identical objects and identity.
3. **Given** a table-cell projection with explicit native cell geometry, **When** it is
   materialized, **Then** the descriptor carries both the cell anchor and exact visual
   page region; if only containing-table geometry exists, the result is labelled as a
   table-level fallback rather than a cell-exact crop.
4. **Given** an unsupported source, missing geometry, stale projection or unavailable
   optional renderer, **When** materialization is requested, **Then** it fails with a
   stable body-free reason and publishes no reachable visual record.

---

### User Story 2 - Escalate Context to Verified Visual Handles (Priority: P2)

As a context consumer, I can request VISUAL evidence and receive current verified
visual handles when they exist, or an explicit missing/escalation notice when they do
not, without receiving fabricated OCR, captions or inaccessible paths.

**Why this priority**: Progressive disclosure is truthful only when the compiler can
distinguish available visual evidence from a request that still needs escalation.

**Independent Test**: Compile identical VISUAL contexts before materialization, after
materialization and after the document head changes; compare bundle items, receipts,
missing evidence, freshness decisions and deterministic replay.

**Acceptance Scenarios**:

1. **Given** no current visual artifact, **When** VISUAL context is compiled, **Then**
   the existing `visual_evidence_required` notice remains present and no pseudo-handle
   is emitted.
2. **Given** a verified current visual descriptor relevant to the exact snapshot,
   **When** VISUAL context is compiled, **Then** it can be selected as a
   `visual_handle`, its handle is object-scoped and its body-free receipt records the
   exact selection and cost.
3. **Given** a visual artifact from an older source or different representation,
   **When** current-only context is compiled, **Then** it is excluded as stale and the
   current request remains honestly unsatisfied.
4. **Given** a tampered descriptor, crop, page raster or catalog binding, **When** the
   compiler discovers candidates, **Then** compilation fails closed rather than
   returning an unverifiable handle.

---

### User Story 3 - Add Optional OCR or Caption Interpretations Safely (Priority: P3)

As an enrichment component, I can attach an explicitly requested local OCR or caption
provider behind a narrow interface and publish its bounded result as an untrusted,
reproducible derivation of exact visual bytes.

**Why this priority**: OCR and captions are useful, but confusing them with source
truth would undermine the evidence model.

**Independent Test**: Use deterministic fake offline providers to publish OCR and
caption results, then vary provider/version/model/config/input and assert derivation
identity, trust, invalidation and output bounds without any network access.

**Acceptance Scenarios**:

1. **Given** an exact visual artifact and an explicitly configured offline OCR
   provider, **When** interpretation runs, **Then** the output records the visual input
   digest, complete provider recipe, confidence when supplied and untrusted derived
   classification.
2. **Given** the same exact inputs and provider recipe, **When** interpretation is
   retried, **Then** publication converges; changing input, provider, model or config
   creates a distinct derivation.
3. **Given** no provider, a network attempt, timeout, cancellation, oversized output or
   malformed result, **When** interpretation is requested, **Then** it fails closed and
   does not promote partial or unverified output.
4. **Given** low-confidence OCR, **When** it is offered to a context consumer, **Then**
   the exact original crop handle remains available alongside it and the OCR alone
   cannot satisfy a visual-evidence requirement.

---

### User Story 4 - Preserve Security, Rights and Operational Truth (Priority: P4)

As a workspace operator, I can upgrade safely, inspect body-free visual records and
rely on strict resource, metadata, licensing and export restrictions across crashes,
concurrency and hostile fixtures.

**Why this priority**: Raster decoding and document rendering process complex untrusted
data and must not weaken local-first or evidence-preservation guarantees.

**Independent Test**: Exercise synthetic decompression bombs, malformed dimensions,
huge pages, deceptive text, abusive metadata, cancellation/fault injection, concurrent
materialization and revision upgrade/rollback fixtures on every supported platform.

**Acceptance Scenarios**:

1. **Given** valid revision-7 workspaces, **When** initialization runs, **Then** one
   additive checksummed migration installs visual reachability while preserving every
   prior fact and public contract.
2. **Given** a decompression bomb, unsafe dimensions, excessive pixels/bytes/pages,
   multi-frame image or abusive metadata, **When** rendering or cropping begins,
   **Then** a configured bound stops the operation with no reachable partial output.
3. **Given** unknown rights or document-embedded license claims, **When** a visual
   descriptor is created, **Then** its effective policy remains trusted-configured or
   conservative local-only and export-denied.
4. **Given** a crash after immutable object publication but before catalog commit, or
   concurrent identical requests, **When** the request retries, **Then** catalog state
   converges to one complete record; complete unreachable residue is left for F013.

### Edge Cases

- Zero-page, encrypted, malformed or unsupported source; page number zero/past end;
  renderer dependency absent; provider-native artifact or projection unavailable.
- Negative, zero-area, non-finite, overflowed or out-of-bounds regions; a valid region
  that rounds to one pixel; a crop spanning the complete page; one-unit PPM edge drift.
- PDF rotations 0/90/180/270, declared page dimensions that disagree with rendered
  orientation/aspect beyond the 1,000-PPM admission bound, very small/large scales and
  platform-specific raster encoders.
- Table cell with merged row/column spans, multiple provenance records, cell geometry
  absent, cell geometry outside table geometry or only whole-table provenance.
- Picture pointer with no page provenance, deceptive invisible text, annotation layers,
  EXIF orientation/GPS/ICC payloads, animated/multi-frame images and alpha channels.
- Encoded bytes below the limit that expand beyond pixel/output limits, huge page count,
  timeout, worker crash, cancellation before/during/after object publication and disk
  exhaustion at catalog commit.
- Concurrent identical materializations, same crop under different recipes, current
  head changing during materialization and descriptor/crop/page object digest drift.
- OCR/caption output containing prompt injection, control characters, excessive text,
  unsupported confidence, mismatched input identity or a provider attempting egress.

## Requirements

### Functional Requirements

- **FR-001**: F011 MUST materialize visual evidence only from an exact committed source
  version and accepted READY rich representation whose F006 native/reference/projection
  records and all referenced CAS objects have been reverified.
- **FR-002**: One requested visual target MUST be an accepted F006 page-region,
  picture/provider-pointer or table-cell projection; arbitrary paths, URLs, raw native
  pointers and unregistered source bytes MUST NOT be accepted at the public boundary.
- **FR-003**: The feature MUST add one thin experimental visual descriptor that binds
  exact document/source/representation/native/reference/projection identities, target
  anchor, resolved page region, granularity, raster/crop objects, dimensions,
  transform, recipe, timestamps, trust and usage restrictions without reproducing a
  complete page or provider-native model.
- **FR-004**: Visual-descriptor identity MUST use a documented domain-separated RFC
  8785/SHA-256 projection over every semantic input; page-raster and crop bytes MUST
  retain their direct SHA-256 CAS identities. Golden vectors MUST cover all identity
  inputs and prove unrelated operational metadata is excluded.
- **FR-005**: F006 normalized PPM top-left coordinates MUST map to display-raster pixels
  deterministically using floor left/top and ceiling right/bottom, positive half-open
  bounds and no clamping, repair or persisted binary floating-point arithmetic; any
  overflow, mismatch or zero area MUST fail closed.
- **FR-006**: The descriptor MUST record provider coordinate system, normalized region,
  rendered pixel extent, crop pixel rectangle, source page size, source rotation,
  applied rotation and rational render scale sufficient to audit the transform. Before
  cropping, provider-native and rendered display aspect ratios MUST agree within the
  recipe's fixed 1,000-PPM relative-error bound after rotation, or fail with
  `page_geometry_mismatch` without inferred stretching.
- **FR-007**: Table-cell evidence MUST preserve its exact zero-based row/column/spans
  and containing table pointer. Cell-exact visual granularity requires explicit native
  cell geometry; otherwise only explicit containing-table fallback is allowed and MUST
  carry a stable warning.
- **FR-008**: Provider-pointer resolution MUST remain profile/version scoped, bounded
  and limited to the exact retained native JSON. F011 MUST NOT interpret arbitrary
  pointer formats, deserialize executable objects or claim cross-provider equivalence.
- **FR-009**: Rendering and raster decoding MUST sit behind narrow provider-neutral
  ports. The default core install remains dependency-free beyond existing core
  requirements; the concrete PDF/raster path is an explicitly selected, exactly locked,
  local-only optional capability.
- **FR-010**: The initial concrete renderer MUST support deterministic bounded PDF page
  rasterization and deterministic single-frame lossless crop encoding on Linux, macOS
  and Windows. Because native wheel output can differ by platform, the persisted recipe
  MUST bind the exact installed renderer and encoder wheel contents; unsupported rich
  media MUST return a stable unavailable result through the same provider-neutral
  service contract.
- **FR-011**: Renderer/decoder execution MUST use bounded killable isolation with
  explicit encoded-source, page-count, page-dimension, total-pixel, crop-dimension,
  decoded-byte, output-byte, metadata, frame-count, elapsed-time, memory where portable
  and file-descriptor limits.
- **FR-012**: Cancellation, timeout, crash, malformed dimensions, decompression-bomb
  detection, unsupported encryption/media, resource excess and storage failure MUST
  map to stable body-free categories, terminate/reap bounded work and expose no
  catalog-reachable partial descriptor.
- **FR-013**: EXIF, document metadata, visible/hidden text and model output MUST be
  treated only as untrusted data. The renderer contract alone controls orientation;
  unsafe metadata MUST be ignored/stripped or cause fail-closed rejection and MUST NOT
  authorize paths, network, policy or tools.
- **FR-014**: Page raster, crop and canonical descriptor objects MUST be published and
  digest/length reverified before one transactional idempotent catalog commit makes the
  complete visual record reachable. Conflicting same-identity records MUST fail closed.
- **FR-015**: Repeated identical materialization MUST reuse and verify the exact record
  without invoking the renderer; changed source, projection/region, renderer version,
  scale, rotation policy, encoder/config or limits affecting output MUST produce a
  distinct recipe and descriptor identity.
- **FR-016**: Visual records MUST be fresh only for their exact source and
  representation snapshot. Context discovery MUST exclude stale/different-scope
  records, reverify descriptor/raster/crop/catalog bindings and never float replay to a
  new document head.
- **FR-017**: Existing ContextBundle `0.2.0` compilation MUST be able to select current
  verified visual records as `visual_handle` items with opaque object-scoped handles,
  exact artifact identity and exhaustive body-free receipt decisions.
- **FR-018**: When no qualifying visual record is available, VISUAL compilation MUST
  preserve the explicit `visual_evidence_required` missing-evidence/receipt notice.
  It MUST NOT render implicitly, synthesize a handle or substitute OCR/caption text.
- **FR-019**: Visual candidate selection and replay MUST remain deterministic,
  budget-bounded and provider-free; descriptor bytes MAY be measured as selection cost,
  while image bodies MUST remain handle-only and outside the context JSON payload.
- **FR-020**: OCR and captioning MUST be optional explicit provider-neutral ports with
  no default implementation or egress. Provider recipe, model identity, config/prompt
  identity, exact visual input hash, bounds, confidence where present and creation time
  MUST be recorded for every accepted interpretation.
- **FR-021**: OCR/caption outputs MUST remain `model_derived` or equivalently untrusted
  derived data with role `data` and instruction execution false; they MUST publish
  through the F010 derivation lifecycle with the exact crop object as dependency and
  never replace or increase the trust of original visual evidence. Current-snapshot use
  MUST independently require the parent visual descriptor's exact scope to remain
  current; F011 MUST NOT claim that F010 automatically stales object-only dependencies
  on a document-head change.
- **FR-022**: Low-confidence or absent OCR MUST retain an exact crop handle for
  verification. OCR/caption output alone MUST NOT satisfy `VISUAL_HANDLE`, exact quote
  or source-verification requirements.
- **FR-023**: Effective licensing and export fields MUST come only from a trusted
  out-of-band policy port. Unknown rights default to `local_only`, export false and a
  stable restriction code; document/EXIF/model claims cannot relax the policy.
- **FR-024**: The feature MUST expose bounded local CLI/application operations to
  materialize and inspect visual evidence using registered identifiers. It MUST NOT add
  a path-taking visual API, network service, MCP mutation tool, watcher or background
  scheduler.
- **FR-025**: Checksummed workspace migration 8 MUST be additive, transactional,
  restart/concurrency safe and downgrade-honest. Visual descriptor, page-raster and crop
  references MUST enter reachability analysis; missing/drifted objects are integrity
  failures, not silent omissions.
- **FR-026**: The experimental visual descriptor schema, valid/invalid fixtures and
  identity vectors MUST use JSON Schema 2020-12, exact version support, closed direct
  fields and deterministic generation/drift checks. An accepted ADR MUST define the new
  contract, identity, provider and compatibility boundaries before implementation.
- **FR-027**: Existing eleven public schemas, their bytes/vectors, F006 evidence corpus,
  F007 provider profile/native export, F008 bundle/receipt identity and F009 MCP
  descriptors MUST remain byte-for-byte and semantically unchanged.
- **FR-028**: Logs, catalog rows, receipts, CLI errors and diagnostics MUST contain only
  identifiers, digests, dimensions/counts, stable codes and timings by default -- never
  page/crop bytes, OCR/caption bodies, task text, source paths, metadata, secrets or
  traceback details at the public boundary.
- **FR-029**: Synthetic or redistributable offline tests MUST cover exact geometry,
  rotation/scale, page/image/table/cell retrieval, unsupported paths, decompression and
  dimension bombs, metadata abuse, prompt injection, cancellation/crash, cache reuse,
  concurrency, migration, reachability, context freshness and optional-provider
  contracts on Linux, macOS and Windows.
- **FR-030**: Documentation MUST state supported media/capability boundaries, exact
  commands, limits, trust and rights semantics, visual-context workflow, optional
  dependency supply chain, rollback/recovery behavior and residual renderer risks
  without universal fidelity or sandbox claims.

### Non-Goals and Compatibility Impact

- **Non-goal**: No complete provider-neutral page/layout model, cross-provider visual
  equivalence, semantic image understanding or guarantee that rendering matches every
  proprietary application.
- **Non-goal**: No built-in OCR, caption, vision-language or cloud provider; no automatic
  model download, external call, credential handling or mandatory embedding.
- **Non-goal**: No automatic reparse, watching, durable scheduling/cancellation job or
  background worker orchestration (F012).
- **Non-goal**: No deletion, quarantine, garbage collection, backup/restore or orphan
  cleanup (F013); complete pre-commit CAS residue remains a documented recovery input.
- **Non-goal**: No export package (F014), new MCP tool or mutation, HTTP surface,
  arbitrary native query, filesystem-path input or bidirectional document editing.
- **Compatibility impact**: Additive experimental visual-descriptor `0.1.0`, additive
  workspace revision 8, internal domain/port/service and CLI behavior, one accepted ADR
  and an optional exactly locked visual dependency group. Existing public contract,
  provider-profile, native-export and MCP versions remain unchanged.

### Key Entities

- **Visual Materialization Request**: Exact accepted evidence target plus bounded render
  recipe, scale, usage policy context and cancellation boundary.
- **Visual Source Raster**: Immutable page display raster derived from exact source bytes
  by one versioned renderer recipe; reusable by multiple crops.
- **Visual Region**: F006 anchor resolved to one normalized top-left page rectangle with
  explicit granularity and any conservative fallback warning.
- **Pixel Transform**: Auditable mapping between source/provider page coordinates,
  normalized coordinates and half-open rendered/crop pixel rectangles.
- **Visual Evidence Descriptor**: Thin canonical CAS record binding identities,
  geometry, objects, provenance, trust, freshness basis and rights restrictions.
- **Visual Catalog Record**: Body-free transactional reachability projection used for
  cache reuse, inspection, context discovery and integrity verification.
- **Visual Usage Policy**: Trusted local-only/export decision and bounded restriction
  codes independent of document-provided metadata.
- **Visual Interpretation Provider**: Optional OCR or caption port whose result becomes
  an untrusted F010 derivation of the exact crop artifact.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every labelled region in a synthetic 100-case geometry corpus produces
  the exact expected half-open pixel rectangle across rotations/scales/platforms; no
  out-of-bounds or wrong-page crop is accepted.
- **SC-002**: Identical source, target and exact wheel-bound recipe requests produce
  byte-identical page, crop and canonical descriptor objects across 20 fresh processes
  on each Linux/macOS/Windows CI runner; platform-specific wheel recipes have distinct
  identities rather than being falsely treated as byte-equivalent. Cache hits invoke
  the renderer zero times.
- **SC-003**: All table-cell cases with explicit geometry are cell-exact; all cases
  without it are either rejected or explicitly labelled table-level fallback, with zero
  falsely labelled cell-exact results.
- **SC-004**: Every malformed/decompression/dimension/metadata/frame/output-limit
  fixture fails within configured bounds and exposes zero catalog-reachable partial
  visual records.
- **SC-005**: Fault/cancellation injection at every worker, CAS and catalog boundary
  leaves either no reachable record or one complete verifiable record; retry converges
  under 20 concurrent identical requests.
- **SC-006**: VISUAL context before materialization reports
  `visual_evidence_required`; after materialization it selects a verified handle; after
  head change it excludes the old record in 100% of freshness fixtures.
- **SC-007**: Optional fake OCR/caption providers show exact derivation identity and
  invalidation for every changed input/provider/model/config, zero trust promotion and
  zero network access.
- **SC-008**: Revision-7-to-8 upgrade succeeds for fresh and populated workspaces;
  injected failure preserves revision 7 facts; concurrent initialization converges to
  one checksummed revision 8 and older software fails too-new without mutation.
- **SC-009**: Freeze tests prove zero byte/semantic drift in all eleven existing public
  schemas, F006 fixtures/vectors, F007 profile/export facts, F008 identities and F009
  descriptor fixtures.
- **SC-010**: Ruff, format, strict mypy, all network-disabled tests with branch coverage,
  build, schema/repository validation and Linux/macOS/Windows CI pass with reviewed
  lockfile and optional-dependency evidence.

## Assumptions

- F006/F007 have already committed the exact accepted projection and retained native
  artifact; F011 does not repair or reinterpret incomplete ingestion records.
- A visual crop is a derived display view, not a replacement for original bytes. The
  source and page raster remain reachable so the crop can be audited and reproduced.
- Historical OCR/caption artifacts remain intrinsically valid for their exact crop even
  after a document head changes. They are ineligible for current-snapshot use when the
  parent visual scope is no longer current; no unsupported F002 lineage is fabricated.
- PDF is the only concrete page renderer required in the first local implementation.
  DOCX/PPTX visual resolution remains provider-neutral and honestly unavailable until
  a reviewed renderer supplies exact page rasters.
- Explicit materialization before context compilation preserves F008 deterministic
  compilation and avoids hidden provider execution. Existing MCP compilation can read
  verified visual records but gains no renderer authority or new tool.
- A table-cell provider pointer may lack cell geometry. Returning the exact containing
  table with explicit fallback is useful evidence; labelling it cell-exact would not be.
- Rights are deployment facts, not document facts. In the absence of a trusted policy
  integration, local retrieval is allowed for the operator's source while export stays
  denied and the descriptor records unknown rights.
- The optional renderer/decoder dependency can be exactly locked and supported on all
  three CI platforms; its residual native-code risk is bounded and documented, not
  claimed eliminated.
