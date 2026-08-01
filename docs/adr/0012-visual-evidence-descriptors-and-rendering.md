# ADR 0012: Materialize thin visual evidence through an optional bounded renderer

Status: Accepted for Feature 011

Date: 2026-08-01

## Context

F006 defines provider-neutral page-region and table-cell anchors, F007 retains the
complete provider-native artifact, and F008 can report that visual evidence is required.
No accepted contract yet binds an exact rendered page/crop to those facts. Rendering
and image decoding also add native attack surface, output amplification and licensing
questions that cannot be delegated to untrusted document metadata.

Changing F006 identities or creating a complete provider-neutral layout tree would
break existing conformance evidence and violate ADR 0008. Rendering implicitly during
context compilation would give an otherwise provider-free read path new execution
authority and make replay depend on optional runtime availability.

## Decision

### Add one thin experimental descriptor

Feature 011 adds `VisualEvidenceDescriptor 0.1.0`. It composes exact F006/F007 source,
representation, native, reference and projection identities with one resolved page
region, page-raster record, pixel transform, crop object, renderer recipe, trust and
trusted usage policy. It does not reproduce a provider page/table/picture tree.

The visual descriptor identity uses a new versioned RFC 8785/SHA-256 domain and includes
all semantic source, target, geometry, raster, crop, recipe and usage-policy inputs.
Page and crop bytes retain direct SHA-256 CAS identities. Creation time and extension
data do not alter the semantic visual identity. Existing identity projections remain
unchanged.

### Use explicit optional local rendering

Rendering is an explicit application operation over one accepted projection. Context
compilation never invokes a renderer, OCR or caption provider. It may select a current,
already materialized descriptor through the existing handle-only ContextBundle shape;
otherwise it preserves `visual_evidence_required`.

The concrete initial capability is an optional exactly locked PDFium/Pillow adapter for
bounded PDF page rendering and deterministic single-frame RGB PNG cropping. Its recipe
binds SHA-256 fingerprints over the exact installed wheel RECORD contents so distinct
platform-native wheels cannot collide in the raster cache. Core has no renderer
dependency. DOCX/PPTX page rendering remains unavailable until a reviewed provider
implements the same port. The F007 provider profile and native export stay unchanged.

Provider-native normalized top-left PPM coordinates map to half-open display pixels
using integer floor left/top and ceiling right/bottom with no clamping. After declared
rotation, provider and rendered display aspect ratios must agree within a fixed
1,000-PPM relative error or fail closed. Table cells are `cell_exact` only with explicit
cell geometry; explicit containing-table geometry is labelled `table_fallback`.

The optional adapter runs in a spawned killable worker with network denied before
provider import and explicit source, page, dimension, pixel, decoded/output byte,
metadata, frame, time, file and memory limits. This is bounded defense in depth, not a
universal sandbox or rendering-fidelity claim.

### Persist page reuse and visual reachability atomically

Workspace migration 8 adds append-only page-raster and visual-record tables. Immutable
page, crop and descriptor objects are written and reverified in CAS first; one SQLite
transaction inserts or exactly reuses the page raster plus complete visual record.
Page rasters are reusable across crops. Conflicting same-identity results fail closed.
Every referenced object becomes a reachability root.

A crash before catalog commit may leave complete unreachable CAS objects. They are not
partial logical records; F013 owns later classification and cleanup. Older software
rejects revision 8, and rollback requires a paired pre-upgrade workspace backup.

### Keep interpretations optional and untrusted

OCR and captioning remain explicit provider-neutral ports with no registered default.
Accepted bounded outputs publish through F010 using the crop object as an exact object
dependency and remain model-derived untrusted data. An object-only dependency remains
historically valid after a head change; current use separately rechecks that the parent
visual descriptor scope is current. F011 does not fabricate F002 lineages or claim
automatic head-driven staleness for rich projections.

### Default rights policy closed

Only a trusted out-of-band policy port may set effective license/export facts. The
built-in policy is local-only, export denied and `license_unverified`. Document,
provider, EXIF or model metadata cannot relax it. F014 must enforce this descriptor fact.

## Compatibility

- Additive public visual descriptor `0.1.0` and workspace revision 8.
- Existing eleven public schemas, F006 identities/conformance corpus, F007 provider and
  native-export profiles, F008 bundle/receipt identities and F009 MCP descriptors remain
  byte-compatible.
- Application and workspace capabilities advance independently. No export profile
  changes.
- A breaking visual-contract or persisted-identity change requires fixtures, migration
  guidance, changelog and a new ADR.

## Consequences

- Exact visual evidence becomes reproducible, inspectable and progressively retrievable
  without embedding image bytes in context bundles.
- Page rendering is reused across crops and never hidden in a read-oriented compiler.
- The optional native dependency adds residual decoder/renderer risk and cannot promise
  parity with every proprietary viewer.
- Office page rendering and built-in OCR/caption models remain deliberately absent.
- Unknown rights permit local inspection but block later export.

## Alternatives considered

- Extend F006 anchors in place: rejected because it changes frozen identity semantics.
- Create a complete page/layout IR: rejected by ADR 0008 and unnecessary.
- Generate Docling page images by changing F007: rejected because it invalidates an
  unrelated provider profile and retains large eager output.
- Render implicitly in ContextCompiler or MCP: rejected because it expands authority and
  makes replay runtime-dependent.
- Run image/PDF decoding in-process: rejected because hostile decoding is a primary F011
  threat.
- Trust embedded license metadata: rejected as an untrusted policy escalation.
