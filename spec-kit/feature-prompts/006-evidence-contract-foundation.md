# Feature 006 — Evidence contract foundation

## Goal
Define the smallest experimental provider-neutral contracts required before implementing a rich-document adapter.

## Scope
- `NativeRepresentation`, `EvidenceReference`, minimal `EvidenceProjection` and `TrustClassification` models/schemas.
- Source-version-bound text, page-region, table/cell and opaque provider-pointer anchor variants.
- Strict version/stability metadata, extension policy and canonical identity projection.
- Golden valid/invalid fixtures and an adapter-independent validator.
- W3C PROV/Web Annotation mapping guidance without making those mappings mandatory wire fields.

## Constraints
Do not encode Docling node classes, SQLite rows, filesystem paths or ranking logic in provider-neutral contracts. Unknown-field behavior and unsupported-major-version behavior must be explicit.

## Acceptance
Canonical/digest vectors are deterministic; stale source versions, invalid geometry, malformed pointers and trust escalation are rejected; existing Feature-005 schemas remain compatible or receive an explicit migration decision.
