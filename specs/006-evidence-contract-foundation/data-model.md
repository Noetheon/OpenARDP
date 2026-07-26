# Data Model: Evidence Contract Foundation

## Shared contract metadata

Every root is closed and includes:

| Field | Rules |
|---|---|
| `contract_version` | Installed semantic release; F006 supports exactly `0.1.0` |
| `stability` | Constant `experimental` |
| `extensions` | URI-namespaced keys to JCS/I-JSON values; excluded from identities |

Malformed versions, uninstalled releases, and unsupported majors have distinct
diagnostics. Application, workspace, provider-profile, and export-profile versions are
not inferred from `contract_version`.

## NativeRepresentation

An immutable record for the complete provider-native artifact.

| Field | Rules | Identity-significant |
|---|---|---:|
| `native_representation_id` | Recomputed SHA-256 JCS identity | declared output |
| `source_version_id` | Exact original-byte SHA-256 | yes |
| `native_artifact_id` | SHA-256 of retained native bytes | yes |
| `native_artifact_media_type` | Non-empty IANA-style media type | yes |
| `native_artifact_byte_length` | Integer `>= 0`, I-JSON safe | no |
| `provider.name` | Stable provider/component name | yes |
| `provider.version` | Generator implementation version | yes |
| `provider.profile` | Provider profile name | yes |
| `provider.profile_version` | Independent semantic profile version | yes |
| `provider.config_hash` | Exact configuration SHA-256 | yes |
| `created_at` | RFC 3339 UTC timestamp | no |

Identity domain: `openardp:native-representation`.

The model is immutable after construction. A changed provider recipe or native artifact
creates a different identifier; byte length and creation time are integrity/lifecycle
facts but do not redefine canonical content identity.

## ProviderPointer

A nested provider-profile-scoped value:

| Field | Rules |
|---|---|
| `provider_profile` | Non-empty profile name |
| `provider_profile_version` | Valid semantic version, independently governed |
| `pointer_format` | Non-empty bounded format identifier |
| `pointer` | 1–2048 Unicode characters; no C0/C1 controls or DEL |

The value is hashed as data and is never resolved by contract validation.

## Anchor union

### TextSpanAnchor

| Field | Rules |
|---|---|
| `anchor_type` | `text_span` |
| `coordinate_system` | `unicode_code_points` |
| `start` | Safe integer `>= 0` |
| `end` | Safe integer `> start` |
| `text_length` | Optional safe integer `>= end` |

Offsets are half-open. They apply only to the profile-defined text view of the bound
native representation.

### PageRegionAnchor

| Field | Rules |
|---|---|
| `anchor_type` | `page_region` |
| `coordinate_system` | `normalized_ppm_top_left` |
| `page_number` | One-based integer |
| `x`, `y` | Integer parts-per-million from `0` through `999_999` |
| `width`, `height` | Positive integer parts-per-million |

`x + width <= 1_000_000` and `y + height <= 1_000_000`.

### TableCellAnchor

| Field | Rules |
|---|---|
| `anchor_type` | `table_cell` |
| `table` | One `ProviderPointer` to the containing native table |
| `row_index`, `column_index` | Zero-based safe integers |
| `row_span`, `column_span` | Positive safe integers; default `1` |

Index-plus-span arithmetic must remain inside the I-JSON safe integer range.

### OpaqueProviderPointerAnchor

| Field | Rules |
|---|---|
| `anchor_type` | `provider_pointer` |
| `target` | One `ProviderPointer` |

No neutral meaning is inferred from pointer bytes.

## EvidenceReference

One source/native binding and exactly one anchor.

| Field | Rules | Identity-significant |
|---|---|---:|
| `evidence_reference_id` | Recomputed declared identity | declared output |
| `source_version_id` | Exact original source SHA-256 | yes |
| `native_representation_id` | Bound native record SHA-256 | yes |
| `anchor` | Discriminated anchor union | yes |

Identity domain: `openardp:evidence-reference`.

Cross-record validation requires that the referenced `NativeRepresentation` exists and
has the same `source_version_id` and `native_representation_id`.

## TrustClassification

An explicit anti-escalation security record.

| Field | Rules |
|---|---|
| `origin_zone` | `local_trusted`, `organization_trusted`, `external_untrusted`, or `model_derived` |
| `effective_zone` | Same enum, restricted by transition policy |
| `role` | Constant `data` |
| `instruction_execution_allowed` | Constant `false` |
| `integrity` | `verified_sha256` or `unverified` |
| `sensitivity` | Existing sensitivity vocabulary |

Allowed transitions:

| Origin | Allowed effective zones |
|---|---|
| `local_trusted` | `local_trusted`, `organization_trusted`, `external_untrusted`, `model_derived` |
| `organization_trusted` | `organization_trusted`, `external_untrusted`, `model_derived` |
| `external_untrusted` | `external_untrusted`, `model_derived` |
| `model_derived` | `model_derived` |

This lattice permits conservative downgrade and derived classification but no promotion.

## RetrievalHandle

| Field | Rules |
|---|---|
| `artifact_id` | SHA-256 of immutable retrieval bytes |
| `media_type` | Non-empty IANA-style media type |
| `byte_length` | Safe integer `>= 0` |

It is not a local path, URL, signed capability, or instruction to fetch.

## ProjectionProvenance

| Field | Rules | Identity-significant |
|---|---|---:|
| `generator_name` | Non-empty component name | yes |
| `generator_version` | Non-empty implementation version | yes |
| `generator_config_hash` | SHA-256 of projection configuration | yes |
| `created_at` | RFC 3339 UTC | no |

## EvidenceProjection

A thin immutable projection record.

| Field | Rules | Identity-significant |
|---|---|---:|
| `evidence_projection_id` | Recomputed declared identity | declared output |
| `source_version_id` | Must equal embedded reference source | yes |
| `native_representation_id` | Must equal embedded reference native ID | yes |
| `reference` | Complete `EvidenceReference` | reference ID only |
| `retrieval` | Immutable retrieval handle | artifact ID and media type |
| `parent_projection_id` | Optional projection identity | yes |
| `ordinal` | Safe integer `>= 0` | yes |
| `trust` | Anti-escalation classification | no |
| `provenance` | Generator recipe and time | recipe yes, time no |

Identity domain: `openardp:evidence-projection`.

The projection has no arbitrary structured content, provider node tree, ranking field,
filesystem locator, model prompt, mutable head, or executable URI.

## Cross-record validation

The pure aggregate validator accepts one native representation, references, projections,
and an optional expected source version. It enforces:

1. all records use an installed evidence contract release;
2. every reference matches the native source and representation identity;
3. every projection matches its embedded reference and native record;
4. every declared identity recomputes from its allowlist;
5. an optional caller-pinned source version matches every record;
6. duplicate reference or projection identifiers with non-identical records are rejected.

It performs no I/O and returns validated immutable records or a sanitized error.
