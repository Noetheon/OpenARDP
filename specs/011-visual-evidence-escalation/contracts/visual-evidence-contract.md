# Visual Evidence Descriptor 0.1.0 Contract

## Status

Additive experimental contract. The generated normative schema is
`schemas/visual-evidence-descriptor.schema.json`; examples and identity vectors are
conformance evidence, not permission to weaken runtime verification.

## Root

The only new public root is `VisualEvidenceDescriptor`. Direct fields are closed.
Extensions are inert JSON values under absolute-URI namespace keys.

## Authority and trust

- Original source bytes are authoritative.
- Page rasters and crops are exact reproducible derived display views.
- Descriptor metadata is derived navigation/provenance data.
- OCR/captions are separate model-derived interpretations and never fields of this root.
- Document/native/image metadata cannot set trusted policy or export rights.

## Identity

`visual_evidence_id` is lower-case `sha256:` plus the RFC 8785 digest of the versioned
domain envelope documented in `data-model.md`. Every semantic source, target, geometry,
raster, crop, recipe and rights-policy input participates. Creation time and extensions
do not.

Existing identity domains are unchanged.

## Coordinate contract

- Source anchor: accepted F006 discriminated anchor.
- Resolved crop anchor: F006 `PageRegionAnchor` in `normalized_ppm_top_left`.
- PPM scale: exactly `1_000_000`.
- Page number: one-based.
- Pixel rectangle: integer half-open `[left, right) x [top, bottom)`.
- Rounding: floor left/top, ceiling right/bottom using integer arithmetic.
- Clamping/repair: prohibited.
- Rotations: exactly 0/90/180/270 degrees and explicitly recorded.
- Scale: positive bounded numerator/denominator; no persisted binary float.
- Provider/rendered display aspect: fixed-point comparison after rotation, at most
  1,000 PPM relative error for the canonical profile; otherwise
  `page_geometry_mismatch`.

## Table granularity

- `cell_exact` requires explicit native cell provenance.
- `table_fallback` requires explicit containing-table provenance and warning
  `table_geometry_fallback`.
- Row/column/spans and the opaque table pointer always remain visible.
- Inference from cell count, text, OCR or a model is prohibited.

## Retrieval contract

The descriptor refers to `image/png` RGB page and crop objects through exact SHA-256 and
byte length. It carries no filesystem path, URL, credential, executable locator or
base64 image body. Consumers retrieve only registered object-scoped handles and must
rehash before use.

## Rights contract

Unknown rights produce:

```json
{
  "scope": "local_only",
  "export_allowed": false,
  "license_id": null,
  "restriction_codes": ["license_unverified"]
}
```

Only a trusted out-of-band policy provider may produce a less restrictive value. F014
must enforce `export_allowed=false` and restriction codes.

## Compatibility

- Additive visual contract `0.1.0` and workspace revision 8.
- No change to F002/F006/F008/F009 schema bytes or version negotiation.
- No change to F007 provider-profile/native-export identities.
- Unsupported visual-contract major/minor versions fail closed.
- A breaking experimental change requires fixtures, migration/reset guidance,
  changelog and an ADR.

## Failure behavior

Public operations reduce failures to stable body-free codes. They do not echo source,
native, image, OCR/caption, metadata, path, provider exception or traceback content.

## Conformance minimum

Valid fixtures cover page, region, cell-exact and table-fallback descriptors. Invalid
fixtures cover identity drift, scope mismatch, trust promotion, rights mismatch,
coordinate overflow/rounding drift, illegal rotation/scale, object mismatch, missing
fallback warning, unsupported version and unsafe extensions.
