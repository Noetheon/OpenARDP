# Data Model: Visual Evidence Escalation

## 1. Contract versioning

- Visual descriptor contract: experimental `0.1.0`.
- Identity version: `1` with RFC 8785 canonical JSON and domain-separated SHA-256.
- Workspace schema: additive revision `8`.
- Existing F002/F006/F008/F009 contract versions remain unchanged.
- F007 provider profile and native export profile remain unchanged.

## 2. Visual render limits

`VisualRenderLimits` is a closed internal model containing encoded-source/raster bytes,
page count, page/crop dimensions and pixels, decoded/output bytes, metadata bytes,
frame count, timeout, address-space and open-file limits. Every positive value is within
I-JSON safe integer bounds. Aggregate invariants ensure one output fits its aggregate
limit and RGB decoded-byte caps cover the selected pixel cap.

## 3. Render recipe

`VisualRenderRecipe` contains:

- renderer name/version/profile;
- encoder name/version/profile;
- exact rational scale numerator/denominator;
- color mode and opaque background;
- annotation/form/orientation/metadata policy tokens;
- limits configuration hash;
- complete recipe `config_hash`.

The canonical installed profile is provider-neutral at the service boundary and PDFium/
Pillow-specific only in the optional adapter.

## 4. Usage policy

`VisualUsagePolicy` contains:

- `scope`: `local_only` or `export_allowed`;
- `export_allowed`: exact boolean consistent with scope;
- optional bounded reviewed `license_id`;
- sorted unique restriction codes;
- trusted policy provider name/version/config hash.

The built-in policy is `local_only`, `export_allowed=false`, no license id and
`license_unverified`.

## 5. Page raster descriptor

`VisualPageRaster` is an internal immutable record containing:

- `raster_id`: identity over exact source/representation/page/recipe facts;
- exact `RepresentationScope` and source object;
- accepted native representation identity;
- one-based page number;
- source page width/height as bounded exact decimal strings;
- source rotation (`0`, `90`, `180`, `270`);
- applied rotation and rational scale;
- output pixel width/height, `image/png`, RGB mode;
- exact raster `StoredObject`;
- renderer recipe and deterministic creation time.

`raster_id` excludes output bytes so the recipe key can locate a cached result; record
validation verifies that all declared facts match the identity. Catalog conflict logic
rejects a different object for the same raster identity.

## 6. Visual region resolution

`ResolvedVisualRegion` contains:

- original F006 target anchor;
- exact `PageRegionAnchor` used for cropping;
- granularity: `page_exact`, `region_exact`, `cell_exact` or `table_fallback`;
- optional `TableCellAnchor` for cell targets;
- resolved provider pointer where applicable;
- sorted unique warning codes.

Invariants:

- `cell_exact` and `table_fallback` require a table-cell anchor;
- `table_fallback` requires `table_geometry_fallback` warning;
- exact non-table granularity cannot carry a cell anchor;
- fallback never changes the original target anchor.

## 7. Pixel transform

`VisualPixelTransform` contains:

- coordinate system `normalized_ppm_top_left` and scale `1_000_000`;
- normalized x/y/width/height;
- full raster width/height;
- half-open crop left/top/right/bottom;
- source/applied rotation and rational render scale.
- observed fixed-point page-aspect error in PPM, bounded by the canonical recipe's
  `max_page_aspect_error_ppm=1_000`.

Validation recomputes floor/ceiling integer mapping and requires exact equality, positive
area and in-bounds coordinates without clamping. It also recomputes rotation-adjusted
provider/renderer aspect error and rejects values above the recipe bound.

## 8. Visual evidence descriptor (public root)

`VisualEvidenceDescriptor` contains:

- `contract_version`, `stability=experimental`, `identity_version`;
- `visual_evidence_id`;
- exact document/source/representation/native/reference/projection identities;
- embedded original target anchor and resolved region;
- embedded page raster descriptor and pixel transform;
- exact crop `StoredObject`, media type `image/png`, dimensions and RGB mode;
- render recipe and deterministic creation time;
- source-backed/untrusted `TrustClassification`;
- trusted `VisualUsagePolicy`;
- absolute-URI namespaced JSON extensions.

Validation requires source/native/reference/projection scope agreement, raster/transform/
crop dimension agreement, no trust promotion, and an exact identity projection.

`visual_evidence_id` preimage:

```json
{
  "canonicalization": "RFC8785",
  "domain": "openardp:visual-evidence",
  "identity_version": 1,
  "payload": {
    "source_version_id": "...",
    "representation_id": "...",
    "native_representation_id": "...",
    "evidence_reference_id": "...",
    "evidence_projection_id": "...",
    "target_anchor": {},
    "resolved_region": {},
    "raster_id": "...",
    "transform": {},
    "crop_object_id": "...",
    "crop_media_type": "image/png",
    "recipe": {},
    "usage_policy": {}
  }
}
```

Creation time and extension data are excluded from identity. The canonical descriptor
object itself includes them and is independently content-addressed.

## 9. Catalog commit and record

`VisualEvidenceCommit` contains a validated page raster, descriptor, raster record
object, descriptor object and crop object. Canonical object descriptors are recomputed
before acceptance.

`VisualEvidenceRecord` is the complete body-free catalog projection:

- descriptor id/object;
- exact scope and target projection id;
- raster id/object;
- crop object;
- page number, granularity and canonical-context-profile flag;
- creation time and row fingerprint.

The row fingerprint covers all fields except itself. Exact retries return the existing
record; any semantic difference for the same descriptor/raster identity conflicts.

## 10. Context candidate extension

Internal `ContextCandidate` supports two mutually valid payload shapes:

1. content candidate: body object/media type and no artifact handle;
2. handle candidate: visual representation, descriptor cost object, opaque CAS handle
   and exact descriptor-object artifact id. The descriptor contains the crop object;
   neither body is embedded in context JSON.

`VisualContextCandidateSource` yields one canonical-profile visual candidate per target
projection in the exact snapshot. Provenance remains the existing
`ContextProjectionProvenance`; the bundle schema is unchanged.

## 11. Interpretation contract

`VisualInterpretationRequest` contains exact descriptor/crop identity, operation
(`ocr` or `caption`), bounded provider recipe and output limits.

`VisualInterpretationResult` contains:

- operation;
- bounded text;
- optional fixed-point confidence in `[0, 1_000_000]`;
- language/region hints as bounded data-only values;
- sorted warning codes.

The service canonicalizes this result, builds a READY F002 `DerivationRecord` with
`model_derived` trust and publishes it to an F010 slot keyed by visual evidence id and
operation. The crop object is an `OBJECT` dependency. Provider/model/config/prompt
changes alter the artifact identity.

An object dependency remains historically valid when a document head changes. Current
use therefore rechecks the parent descriptor's exact scope; F011 does not map rich
projection identity into an unsupported F002 evidence binding.

## 12. State transitions and atomicity

```text
unmaterialized
  -> page/crop/descriptor CAS objects published (unreachable)
  -> one SQLite transaction inserts/reuses page raster + visual record
  -> reachable/current for exact scope

head changes
  -> historical visual record remains immutable
  -> current-only candidate discovery excludes its old scope

interpretation requested
  -> provider returns bounded result
  -> F010 READY/FAILED publication
  -> CURRENT, STALE, FAILED or SUPERSEDED through existing F010 lifecycle
```

No F011 operation deletes objects or rows. F013 later classifies complete unreachable
CAS residue.
