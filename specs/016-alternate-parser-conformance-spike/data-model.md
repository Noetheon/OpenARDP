# Data Model: Alternate Parser Conformance Spike

All records are immutable canonical JSON values. Identifiers are lowercase `sha256:` values
over declared bytes or domain-separated canonical identity envelopes.

## Conformance Manifest

- `profile_version`: exact supported conformance profile version.
- `evidence_manifest`, `identity_vectors`: confined paths plus expected SHA-256 digests.
- `sources`: source kind, confined path, media type and expected raw-byte digest.
- `required_coverage`: root models, anchor classes and producer output classes.
- `limits`: maximum files, bytes, request/response bytes and execution seconds.
- `expected_report`: confined path and digest.

The manifest is closed, sorted and complete. Missing, duplicate, absolute, linked,
escaping, unlisted or digest-drifted inputs invalidate the run.

## Independent Observation

- `case_id`: stable manifest-derived case key.
- `direction`: `reference_to_alternate` or `alternate_to_reference`.
- `kind`: valid root, invalid root, record set, identity vector or producer record.
- `expected`: accept, reject/category or exact digest.
- `observed`: same closed outcome vocabulary.
- `status`: `pass` or `fail`, derived only from expected-versus-observed equality.

Observations are uniquely ordered by `(direction, kind, case_id)`. Duplicate keys or
caller-asserted status values are invalid. The enclosing process response binds the exact
implementation digest; the decision binds the manifest, corpus/vector and source digests
plus the complete ordered observation array.

## Alternate Native Artifact

The TXT native artifact retains decoded text, newline facts and source byte metadata. The
CSV native artifact retains dialect declaration, ordered rows and declared deterministic
page/grid facts. Both include only source-derived data and fixed recipe metadata.

## Alternate Evidence Record Set

- One `NativeRepresentation` bound to source bytes, canonical native bytes and provider
  recipe.
- Ordered `EvidenceReference` values including required text/page/table anchors.
- Ordered `EvidenceProjection` values with retrieval handles, data-only trust and exact
  generation provenance.
- Canonical native/retrieval artifact bytes used to verify every declared byte length and
  digest.

All reference/projection source and native identities must agree. Record identifiers must
be unique for identical semantics and collision-free for different payloads.

## Provider-Neutrality Decision

- `profile_version`, `status`: exact version and `supported_for_scoped_claim` or
  `not_supported`.
- `input_id`, `implementation_id`, `observation_set_id`, `decision_id`: complete identity
  chain.
- `observations`: complete ordered raw expected-versus-observed outcomes used by the decision.
- `coverage`: ordered measured models, anchors, directions and source types.
- `friction`: ordered findings with contract surface, severity and disposition.
- `provider_leakage`: ordered findings; empty is an explicit measured result.
- `verified_claims`: allowlisted narrow claims derived from passing observations.
- `prohibited_claims`: fixed non-claims including stabilization and semantic equivalence.
- `required_changes`, `limitations`: ordered traceable outcomes.

### State transition

`inputs_verified` → `alternate_consumed` → `alternate_produced` →
`reference_consumed` → `decision_generated`.

Any missing, invalid, timed-out or inconsistent mandatory observation transitions directly
to `not_supported`; no transition returns to a passing state without a complete new run.
