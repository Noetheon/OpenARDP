# Research: Visual Evidence Escalation

## Decision 1: Extend F006 anchors; do not create a page model

**Decision**: F011 introduces a single thin `VisualEvidenceDescriptor 0.1.0` that
references an accepted F006 projection and records only the resolved page/crop facts
needed for retrieval, verification, trust and lifecycle. It does not change F006 anchor
schemas or reproduce provider-native page/table/picture trees.

**Rationale**: `PageRegionAnchor` already provides one-based page numbers and fixed-point
top-left PPM rectangles. `TableCellAnchor` already provides exact row/column/spans and
an opaque containing-table pointer. ADR 0008 and Constitution Article IV require using
those contracts rather than creating a second complete representation.

**Alternatives considered**:

- Add image/table/cell geometry fields directly to F006 `EvidenceReference`: rejected
  because this breaks experimental identity semantics and existing frozen fixtures.
- Define a complete provider-neutral layout tree: rejected by ADR 0008 and unnecessary
  for retrieval.
- Store only crop bytes: rejected because bytes alone cannot explain source, transform,
  recipe, rights or freshness.

## Decision 2: Explicit materialization, then deterministic context selection

**Decision**: A caller materializes one accepted projection explicitly. F011 adds a
verified visual candidate source to F008 composition so later VISUAL compilation can
select the current handle. The compiler never invokes a renderer, OCR or caption
provider. Existing `visual_evidence_required` behavior remains when no visual record
qualifies.

**Rationale**: Rendering hidden inside candidate discovery would give read-oriented
compilation provider authority, complicate cancellation/atomicity, and make replay
environment-dependent. Explicit materialization keeps F008 selection provider-free and
allows a body-free receipt to explain exactly what existed at the pinned snapshot.

**Alternatives considered**:

- Render implicitly during `compile_context`: rejected because optional provider
  availability would alter compilation and expand F009 read-only behavior.
- Return a renderer request as a visual handle: rejected because it would advertise
  unavailable evidence.
- Add a new MCP rendering tool: rejected; F011 does not add mutation tools.

## Decision 3: Optional PDFium/Pillow reference capability

**Decision**: Add a `visual` optional dependency group pinning `pypdfium2==5.12.1` and
`Pillow==12.3.0`. A spawned local worker uses PDFium for PDF page rasterization and
Pillow for single-frame RGB crop encoding. The core install does not import either.
Unsupported DOCX/PPTX page rendering reports `renderer_unavailable` through the same
port.

**Rationale**: Both exact versions are already present in the reviewed Docling lock
graph, support Python 3.12 and all three CI platforms, and expose the narrow operations
needed. Direct optional declarations make the adapter's packaging dependency honest
rather than relying on an unrelated extra. Pillow metadata declares MIT-CMU;
pypdfium2 reports BSD-3-Clause/Apache-2.0 plus documented bundled dependency licenses.

**Deterministic profile**:

- PDF page index is one-based externally and validated against the document page count.
- Built-in render scale is an exact positive rational; the default is `2/1` pixels per
  PDF canvas unit (144 DPI for ordinary 72-unit pages).
- PDF page rotation is reported by PDFium; no additional caller rotation is applied.
- Annotations and interactive forms are not rendered by the canonical profile.
- Output is flattened to RGB over opaque white and saved as PNG with a fixed compression
  profile and no document/EXIF/text metadata.
- Renderer and encoder profiles include a SHA-256 fingerprint over the installed wheel's
  RECORD hashes. Native wheels may produce different bytes across operating systems;
  those outputs therefore receive different recipe, raster and evidence identities.
- Context eligibility is limited to the installed canonical profile; other future
  recipes remain retrievable but cannot create duplicate candidates for one F006 id.

**Alternatives considered**:

- Depend on Docling page images: rejected because F007 deliberately disables image
  generation and changing that profile would invalidate unrelated native artifacts.
- Use a system browser, Preview or LibreOffice: rejected because it is not deterministic,
  headless or uniformly available.
- Make the libraries core dependencies: rejected because visual evidence remains an
  optional escalation capability.

## Decision 4: Reuse full-page rasters and isolate crop decoding

**Decision**: Materialization caches a canonical page raster record independently from
the final crop record. A new target reuses and rehashes the cached page PNG, then sends
only that registered raster to the same bounded worker for crop decoding. Both page
raster and crop bytes are immutable CAS objects.

**Rationale**: Rendering is the expensive perception step. Reusing an exact page raster
across picture/table/cell crops fulfills the project's redundant-work objective while
keeping derived data disposable. Keeping decoding in the child preserves the same image
bomb and metadata boundary on cache reuse.

**Alternatives considered**:

- Re-render the page for each crop: rejected as avoidable work.
- Crop in the parent process: rejected because untrusted image decoding would escape the
  isolated boundary.
- Persist only cropped pages: rejected because adjacent crops could not reuse rendering.

## Decision 5: Geometry uses exact integer boundaries and explicit granularity

**Decision**: Convert normalized PPM to half-open display pixels as:

```text
left   = floor(x * raster_width / 1_000_000)
top    = floor(y * raster_height / 1_000_000)
right  = ceil((x + width) * raster_width / 1_000_000)
bottom = ceil((y + height) * raster_height / 1_000_000)
```

All arithmetic is integer. Values must have positive area and fit the raster without
clamping. Before mapping, the service compares provider-native and renderer display
aspect ratios after rotation using fixed-point integer arithmetic. The canonical recipe
allows at most 1,000 PPM relative aspect error; larger disagreement fails with
`page_geometry_mismatch` and is never repaired by inferred stretching. The descriptor
records source page extent, source rotation, applied rotation, rational scale,
aspect-error observation, normalized region and final pixel rectangles.

For table cells, the resolver inspects only the accepted table/cell object in retained
native JSON. Explicit cell provenance yields `cell_exact`. If absent, explicit
containing-table provenance yields `table_fallback`; otherwise materialization is
unavailable. Text/model inference is never used for geometry.

**Rationale**: Integer arithmetic avoids cross-platform binary floating ambiguity and
makes every crop auditable. Granularity prevents a whole-table crop from being mistaken
for cell-exact evidence.

**Alternatives considered**:

- Floating-point normalized geometry: rejected because edge rounding can drift.
- Estimate cell rectangles from row/column counts: rejected because merged cells and
  uneven layout make the claim false.
- Always reject table fallback: rejected because exact table-level evidence remains
  useful when truthfully labelled.

## Decision 6: Stable failure taxonomy and bounded worker protocol

**Decision**: The visual port exposes sanitized failures for unsupported media,
dependency unavailable, malformed/encrypted source, page unavailable, region
unavailable, dimension/resource limit, decompression bomb, invalid output, network
denied, timeout, cancellation and worker crash. The spawned protocol carries a strict
operation/config header, bounded byte chunks and one strict JSON metadata plus bounded
page/crop byte result.

Default hard caps:

| Bound | Default |
|---|---:|
| encoded source/raster bytes | 100 MiB |
| document pages | 2,000 |
| page width or height | 20,000 px |
| page pixels | 100,000,000 |
| crop width or height | 10,000 px |
| crop pixels | 25,000,000 |
| decoded RGB bytes | 300,000,000 |
| one PNG output | 100 MiB |
| metadata bytes | 64 KiB |
| frames | 1 |
| elapsed time | 120 s |
| address space where portable | 4 GiB |
| open files | 64 |

The child disables socket creation before provider import, applies portable CPU/file/
address-space limits, and the parent always closes IPC, terminates/kills if necessary
and reaps the process.

**Rationale**: Encoded-byte limits do not protect against decompression bombs. Pixel,
decoded-byte, output and metadata caps must all be independent. This follows the proven
F007 worker pattern while using a separate narrow protocol.

**Alternatives considered**:

- Run native decoding in-process: rejected because malformed images are a primary F011
  threat.
- Rely only on Pillow's global bomb warning: rejected because explicit per-request caps
  and fail-closed errors are required.
- Claim a strong sandbox: rejected; process/resource isolation is defense in depth.

## Decision 7: Atomic visual catalog records and migration 8

**Decision**: Migration 8 adds two append-only tables:

- `visual_page_rasters`: one deterministic raster recipe key, exact scope/page facts,
  raster object, canonical record JSON, timestamp and row fingerprint.
- `visual_evidence_records`: descriptor id, accepted target projection id, raster key,
  canonical descriptor/crop objects, geometry/recipe summary, timestamp and fingerprint.

The service writes and verifies page/crop/descriptor objects first and commits the
raster plus visual record in one transaction. Exact retries converge; conflicting
same-identity payloads fail. Both tables' object ids become reachability roots.

**Rationale**: SQLite provides the accepted local transactional reachability boundary;
CAS-first publication follows ADR 0002. Separate page rows prevent redundant rendering.
Migration 8 is additive and older binaries already reject newer schema histories.

**Alternatives considered**:

- Encode records only as F010 derivation nodes: rejected because visual lookup needs an
  efficient exact projection/page index and the page raster is evidence, not a model
  interpretation.
- Store mutable cache files outside CAS: rejected because identity and integrity would
  be unverifiable.
- Add deletion/cleanup: deferred to F013.

## Decision 8: Existing ContextBundle remains byte-compatible

**Decision**: Extend only internal `ContextCandidate` with a handle payload shape and
add `VisualContextCandidateSource`. A visual item reuses existing
`ContextProjectionProvenance`, representation `visual_handle`, an opaque
`openardp+cas:sha256:<descriptor-object-hex>` handle and matching descriptor-object
`artifact_id`. The verified descriptor then names the exact crop object, geometry and
rights policy. Descriptor/crop bodies remain out of bundle JSON. The ContextBundle
0.2.0 and SelectionReceipt 0.1.0 schemas and identity algorithms do not change.

**Rationale**: The existing contract was intentionally designed for handle-only visual
evidence. Reusing it avoids an unnecessary contract bump. One canonical context recipe
per target avoids duplicate evidence ids.

**Alternatives considered**:

- Add visual geometry to ContextBundle: rejected; consumers can retrieve the descriptor
  through its registered handle and F008 remains thin.
- Embed base64 images: rejected because it violates budgets and progressive disclosure.

## Decision 9: OCR/caption orchestration reuses F010

**Decision**: Define one `VisualInterpreter` protocol with explicit `ocr` and `caption`
capabilities and strict bounded result models. `VisualInterpretationService` verifies
the visual descriptor/crop, invokes an explicitly supplied provider, canonicalizes the
result and publishes it through `DerivationService` with the crop object as an exact
`OBJECT` dependency. No implementation is registered by default.

**Rationale**: F010 already supplies complete generator identity, CAS-first output,
idempotent publication, slot replacement and invalidation. A new parallel lifecycle
would be redundant. Fake deterministic providers can fully test the neutral boundary.

F010 does not automatically stale an `OBJECT` dependency merely because a document
head changes. The interpretation remains historically valid for its exact crop; every
current-snapshot read separately verifies that the parent visual descriptor's scope is
current. F011 does not fabricate an F002 lineage or overstate F010 invalidation.

**Alternatives considered**:

- Store OCR text directly on the visual descriptor: rejected because interpretation is
  neither exact raster evidence nor necessarily available.
- Build a concrete OCR engine now: rejected because the prompt requires optional ports,
  not a mandatory model supply chain.

## Decision 10: Trusted rights policy defaults closed

**Decision**: `VisualUsagePolicyPort` receives body-free registered identifiers and
returns `local_only` or `export_allowed` plus an optional bounded reviewed license id and
sorted restriction codes. The default implementation always returns local-only,
export false and `license_unverified`. Document/native/EXIF/model metadata is never
passed as authority to the port.

**Rationale**: OpenARDP cannot infer copyright permission from document content. A
closed default preserves useful local evidence while giving F014 a machine-enforceable
export restriction.

**Alternatives considered**:

- Trust embedded license metadata: rejected as an untrusted escalation.
- Omit rights fields until export: rejected because downstream packaging must not guess.
- Forbid all local materialization when rights are unknown: rejected because the local
  operator supplied the source and needs inspectable evidence; export remains denied.

## Decision 11: Public contract and compatibility governance

**Decision**: Add ADR 0012 before implementation. Publish
`visual-evidence-descriptor.schema.json` as experimental `0.1.0`, with deterministic
generation, valid/invalid fixtures and identity vectors. Do not modify any existing
schema bytes, F006 identities, F007 profile/export version, F008 identities or F009
descriptors.

**Rationale**: A new persisted public descriptor and identity algorithm require explicit
governance, while an additive experimental root does not require breaking existing
families. Application capability and workspace revision advance independently.

**Alternatives considered**:

- Keep the descriptor undocumented/internal: rejected because retrieval consumers need
  a stable inspectable envelope.
- Bump F006: rejected because the descriptor composes F006 facts rather than changing
  them.

## Residual risks

- PDFium and image codecs are native attack surface; process isolation and limits reduce
  but do not eliminate exploitation risk.
- PDF rendering can differ from proprietary viewers, especially fonts, forms,
  annotations and unsupported features. The profile records its exact renderer and does
  not claim universal fidelity.
- DOCX/PPTX page rendering remains unavailable in the concrete F011 adapter.
- Exact native table-cell geometry is provider/source dependent; fallback remains
  intentionally coarser.
- Unknown rights block export but cannot determine the operator's underlying legal
  entitlement.
