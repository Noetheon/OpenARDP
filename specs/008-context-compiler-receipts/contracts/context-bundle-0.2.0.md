# Contract: Context Bundle 0.2.0 Experimental

## Status and compatibility

F008 adds `schemas/context-bundle-0.2.0.schema.json` while retaining
`schemas/context-bundle.schema.json` as the byte-identical `0.1.0` release. Readers
select the explicitly installed model/schema by `schema_version`. No `0.1.0` field,
identity or acceptance rule changes.

## Why a minor release is required

`ContextBundle 0.1.0` requires every evidence item to cite one F002 block UUID. Accepted
F007 evidence instead cites F006 source/native/reference/projection SHA-256 identities.
A rich projection is not a block; assigning it a synthetic block ID would corrupt
provenance. Version `0.2.0` replaces only the evidence-provenance field with a closed
discriminated union.

## Root shape

The root retains the existing bundle concepts:

- exact `schema_version = 0.2.0`;
- deterministic bundle UUID and corpus-derived UTC timestamp;
- untrusted task/query and mode;
- exact estimator budget;
- unique exact version scopes;
- selected context evidence items;
- compact selection trace, warnings and missing-evidence records;
- JSON-only namespaced extensions.

## Evidence provenance union

### Block provenance

```json
{
  "record_type": "block",
  "document_id": "<uuidv7>",
  "version_id": "sha256:<source>",
  "representation_id": "sha256:<recipe>",
  "block_id": "<canonical uuid>",
  "source": {
    "connector": "local",
    "locator": "<opaque source locator>"
  }
}
```

It carries exactly the prior `0.1.0` block provenance plus the discriminator.

### Projection provenance

```json
{
  "record_type": "evidence_projection",
  "document_id": "<uuidv7>",
  "version_id": "sha256:<source>",
  "representation_id": "sha256:<recipe>",
  "source_version_id": "sha256:<source>",
  "native_representation_id": "sha256:<native>",
  "evidence_reference_id": "sha256:<reference>",
  "evidence_projection_id": "sha256:<projection>"
}
```

`version_id` must equal `source_version_id`. Aggregate validation requires the referenced
F006 projection to match every native/reference/source identity and exact catalog scope.
No provider pointer, native payload or local path is duplicated.

The branches reject each other's fields. Evidence uniqueness uses the complete
scope/discriminator/native evidence identity rather than a fabricated common identifier.

## Context evidence item

The remaining item fields retain the `0.1.0` semantics:

- representation level;
- JSON content or registered artifact handle;
- optional artifact ID where required;
- stable selection reason;
- data-only trust classification;
- namespaced JSON extensions.

Selected content is enclosed in the F008 untrusted-data delimiter object. Visual and
original representations still require registered handles; summaries still require a
derived artifact ID and are not produced by F008.

## Deterministic bundle identity

`bundle_id` is UUIDv5 over:

```text
sha256(RFC8785({
  "canonicalization": "RFC8785",
  "domain": "openardp:context-bundle",
  "identity_version": 1,
  "payload": <all direct semantic bundle fields except bundle_id>
}))
```

The UUID namespace is a fixed documented OpenARDP constant. The model recomputes and
rejects a mismatched UUID. Array order is semantic; extensions are included.

## Budget and aggregate rules

- Every item and missing-evidence scope belongs to `versions`.
- Version scopes and evidence identities are unique.
- An empty item list requires missing evidence.
- Canonical bundle usage plus response reserve cannot exceed the receipt limit.
- Every projection provenance is verified against F006 records before return.
- Trust remains role `data` and cannot be promoted by either provenance branch.

## Evolution

This additive minor is experimental. Removing a provenance branch, weakening scope
checks or changing bundle identity requires a later reviewed contract release and
migration analysis. The existing `0.1.0` schema remains a supported installed reader and
golden fixture throughout F008.
