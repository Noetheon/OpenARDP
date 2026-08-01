# Data Model: Export and Interchange Experiment

## Version constants

- `INTERCHANGE_PROFILE_VERSION = "0.1.0"`
- `INTERCHANGE_RECORD_SCHEMA_VERSION = "0.1.0"`
- `INTERCHANGE_PROFILE_IDENTIFIER` is a stable HTTPS identifier documented by the
  profile; it is metadata only and is never fetched.
- identity and inventory algorithm: `sha256`

## `InterchangePackage`

Closed canonical semantic root:

| Field | Type | Invariant |
|---|---|---|
| `profile_version` | semver | exactly installed `0.1.0` |
| `schema_version` | semver | exactly installed `0.1.0` |
| `package_id` | `sha256:<64 lowercase hex>` | recomputed over record without this field |
| `identity_algorithm` | enum | `sha256-rfc8785-v1` |
| `scope_id` | SHA-256 ID | exact trusted-operator selection |
| `extension_policy` | enum | `reject` or `preserve` |
| `records` | tuple `PortableRecord` | sorted unique `(record_type, record_id)` |
| `assets` | tuple `PortableAsset` | sorted unique `object_id` |
| `relationships` | tuple `PortableRelationship` | sorted unique, endpoints exist |
| `extensions` | JSON object | empty under reject; bounded/preserved under preserve |

Timestamps are excluded from the identity-bearing record. An optional non-normative
operator report may contain observation time.

## `PortableRecord`

| Field | Type | Invariant |
|---|---|---|
| `record_type` | closed enum | source, native_projection, evidence_projection, derivation |
| `contract_version` | exact supported semver | never inferred from app/workspace |
| `record_id` | SHA-256 ID | stable pre-existing or JCS-derived identity |
| `trust` | existing `DataTrustClassification` | data role only; no execution authority |
| `facts` | bounded JSON object | no paths, credentials, body/log fields or unknown top-level keys |
| `extensions` | JSON object | governed by package policy |

The profile does not reproduce provider classes. `facts` is a thin portable projection
whose exact contract version is declared.

## `PortableAsset`

| Field | Type | Invariant |
|---|---|---|
| `object_id` | SHA-256 ID | digest of exact bytes when included |
| `byte_length` | integer | exact non-negative length |
| `media_type` | normalized media type | body-free metadata |
| `role` | closed enum | source or provider_native |
| `disposition` | closed enum | included, referenced or omitted |
| `payload_path` | portable path or null | required only for included |
| `reference` | opaque bounded string or null | required only for referenced; never fetched |
| `omission_reason` | closed enum or null | required only for omitted |
| `redistribution_asserted` | bool | must be true for included |
| `license_assertion` | bounded sender string or null | assertion, not receiver verification |
| `extensions` | JSON object | package policy applies |

Exactly one disposition-specific location/reason is populated.

## `PortableRelationship`

Closed triple of `subject_id`, `predicate` and `object_id`. Predicate is one of
`describes`, `projects`, `derived_from`, `uses_asset` or `has_native_asset`. Every
endpoint exists in `records` or `assets`; tuples are canonical and unique. Cycles are
allowed only for non-derivation predicates. The `derived_from` subgraph is acyclic.

## `InterchangeLimits`

Strict integer limits with documented defaults/ranges for archive bytes, expanded
bytes, entry count, per-entry bytes, metadata bytes, path bytes/depth and relationship
count. Caller overrides can only narrow or select within installed ranges.

## `InterchangeExportRequest`

- one already-validated `InterchangePackage` semantic scope;
- exact `AssetSource` handles keyed by included asset object ID;
- fresh disjoint destination;
- limits.

The adapter reads each included asset once into operation-owned staging while hashing;
the observed digest/length must equal the portable asset facts.

## `PackageInventoryEntry`

Canonical tuple of relative POSIX path, exact byte length, SHA-256 digest and class
(`payload` or `tag`). Payload inventory is rendered into `manifest-sha256.txt`; tag
inventory is rendered into `tagmanifest-sha256.txt`. Manifests use lowercase hex, two
spaces and one LF-terminated entry per canonical sorted path.

## `VerifiedPackage`

Immutable body-free preflight result:

- package ID and profile/schema versions;
- archive SHA-256 and bytes;
- payload/tag entry counts and bytes;
- record/asset/relationship counts;
- canonical inventory entries;
- parsed `InterchangeRecord` retained only inside the trusted service boundary.

## `ImportPlan`

JCS/SHA-256 identity over verified package ID, archive digest, exact target identity,
limits and inventory. It is not persisted. Publication may proceed only from the same
open archive identity; a changed archive invalidates the plan.

## `InterchangeResult`

Body-free machine projection with operation, outcome, package/profile/schema/archive
identities, counts, byte totals and optional stable error category. It never contains
paths, filenames, member bodies, exception strings, references or license text.

## Failure categories

- `MALFORMED_PACKAGE`
- `UNSUPPORTED_VERSION`
- `POLICY_REJECTED`
- `RESOURCE_EXHAUSTED`
- `INTEGRITY_INVALID`
- `RELATIONSHIP_INVALID`
- `SOURCE_CHANGED`
- `DESTINATION_CONFLICT`
- `PUBLICATION_FAILED`

## State transitions

```text
export: request -> staged -> self_verified -> published
                    |             |              |
                    +---------- failed ----------+

import: archive -> preflight_verified -> staged_copy_verified -> published
             |               |                    |             |
             +------------ rejected/failed ---------------------+
```

Only the final rename makes an import snapshot visible. Cleanup is limited to the
current operation's staging path. Existing destinations are never removed or modified.
