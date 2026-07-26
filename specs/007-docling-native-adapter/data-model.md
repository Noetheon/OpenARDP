# Data Model: Docling Native Adapter

## Version dimensions

| Dimension | F007 value/effect |
|---|---|
| Application | remains `0.0.1` during feature development |
| Workspace/catalog | migration `4 → 5` |
| F006 evidence contract | unchanged experimental `0.1.0` |
| Docling provider | exact `2.114.0` |
| Provider profile | `openardp-docling-native` `0.1.0` |
| Native export profile | `openardp-docling-document-json-v1` |
| Projection profile | `openardp-docling-evidence-v1` |
| Export/interchange profile | unchanged; F014 owns export experiments |

## RichMediaType

Closed media allowlist:

- `application/pdf`
- `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- `application/vnd.openxmlformats-officedocument.presentationml.presentation`

Local source inspection derives one of these from an allowlisted suffix. The provider
still validates bytes and rejects malformed/mismatched content.

## RichParserLimits

Immutable validated worker/output bounds:

- `max_source_bytes`
- `max_pages`
- `timeout_seconds`
- `max_address_space_bytes`
- `max_open_files`
- `max_native_bytes`
- `max_projections`
- `max_retrieval_body_bytes`
- `max_total_retrieval_bytes`

Every field has a documented unit, supported range and sanitized failure category.
Values affecting parse/projection behavior enter the recipe configuration digest.

## ModelBundleManifest

Internal strict JSON record for a local PDF model bundle.

| Field | Rule |
|---|---|
| `schema_version` | exactly `0.1.0` |
| `bundle_name` | bounded non-empty identifier |
| `bundle_version` | bounded non-empty version |
| `files` | sorted, unique relative POSIX paths |
| `files[].sha256` | exact lowercase SHA-256 identity |
| `files[].byte_length` | safe non-negative integer |
| `files[].license_id` | reviewed SPDX expression or bounded license reference |
| `extensions` | URI-namespaced safe JSON only |

Validation rejects absolute paths, `.`/`..`, empty parts, backslashes, control
characters, links/non-regular files, escaping resolutions, duplicates, missing files,
length/digest drift and unbounded inventories. The bundle identity is SHA-256 over a
versioned RFC 8785 envelope of the manifest value, excluding the local root path.

## RichParserRecipe

Composes the existing representation `ParserRecipe` and F006 `ProviderRecipe`.

Identity-significant configuration:

- exact Docling version;
- provider-profile and profile version;
- native export and evidence projection profile names/versions;
- supported media and offline pipeline options;
- parser/output limits that affect accepted output;
- optional model-bundle identity;
- explicit absence of OCR, remote services and enrichments.

The local model path, timestamps and operator machine are excluded. The resulting
configuration hash feeds both representation and F006 native identities.

## NativeArtifactDescriptor

Internal immutable reproducibility record.

| Field | Meaning |
|---|---|
| `schema_version` | internal descriptor `0.1.0` |
| `source_version_id` | exact original source SHA-256 |
| `native_representation_id` | matching F006 native identity |
| `provider_native_object` | CAS digest and length of complete JSON |
| `native_media_type` | `application/vnd.docling.document+json` |
| `provider` | exact name/version/profile/profile version/config hash |
| `native_export_profile` | exact export policy |
| `projection_profile` | exact evidence policy |
| `component_versions` | sorted bounded name/version facts |
| `model_bundle_id` | optional path-independent bundle identity |
| `created_at` | UTC lifecycle fact |
| `nondeterminism` | sorted stable warning codes, not prose/body |

The descriptor excludes source/model paths, document bodies and mutable runtime timings.

## RichEvidenceCandidate

Bounded output produced inside the worker before F006 record identity is known.

| Field | Rule |
|---|---|
| `ordinal` | contiguous provider-order integer |
| `parent_ordinal` | optional earlier candidate |
| `kind` | text, heading, table_cell, picture, page or native_pointer |
| `anchor` | one validated F006 anchor |
| `retrieval_media_type` | UTF-8 text or safe JSON |
| `retrieval_bytes` | bounded exact bytes |
| `native_pointer` | reviewed profile-scoped JSON reference |
| `warning_codes` | sorted unique machine tokens |

Candidates contain no provider objects, file paths, executable values or complete native
subtrees.

## RichParseOutput

Strict worker result:

- media type;
- complete canonical native JSON bytes;
- exact decimal-string normalization for Docling's unsigned 64-bit
  `origin.binary_hash` when required by I-JSON/JCS;
- candidate tuple;
- sorted warnings;
- provider/component versions;
- observed native-export warning codes.

Local validators enforce all individual and aggregate bounds, strict JSON, candidate
ordering/parents, anchor/profile rules and absence of untrusted error/body echo.

## F006 records

For one successful parse:

1. Store complete native JSON and compute its CAS identity.
2. Construct one `NativeRepresentation` using exact source, native, provider recipe and
   creation facts.
3. Store each candidate retrieval body and construct one `EvidenceReference`.
4. Construct one `EvidenceProjection` per reference with immutable retrieval handle,
   ordinal, optional parent, external-untrusted/data-only trust and generator provenance.
5. Run `validate_evidence_records` with the exact expected source version.

No F006 public field or identity projection changes.

## RichEvidenceRecord

Internal body-free persistence projection:

- ordinal and optional parent projection ID;
- evidence reference/projection IDs;
- CAS objects for canonical reference, canonical projection and retrieval body;
- retrieval media type and length.

All ordinals are contiguous; IDs are unique; parent IDs precede children; every object
matches the full record embedded in the immutable bundle.

## RichEvidenceBundle

Internal immutable root:

| Field | Meaning |
|---|---|
| `schema_version` | internal `0.1.0` |
| `scope` | document/source/representation identity |
| `descriptor_object` | canonical descriptor CAS object |
| `native_record_object` | canonical F006 native record CAS object |
| `native_representation` | full F006 native record |
| `records` | complete ordered references/projections plus object inventories |
| `created_at` | lifecycle fact |

Bundle validation recomputes all record identities, verifies source/native scope,
requires exact object metadata and rejects duplicate semantic identifiers.

## RichParseAttempt

Append-only evidence for each complete provider execution:

| Field | Rule |
|---|---|
| `attempt_id` | UUIDv7 generated by the service |
| `scope` | exact document/source/recipe representation |
| `outcome` | `CANONICAL`, `CONVERGED` or `DIVERGED` |
| `descriptor_object` | exact canonical descriptor CAS object |
| `provider_native_object` | complete native JSON CAS object |
| `native_record_object` | F006 native record CAS object |
| `evidence_bundle_object` | exact bundle CAS object |
| `projection_count` | matches complete evidence rows |
| `created_at` | UTC execution lifecycle fact |

The first successful commit creates the `CANONICAL` attempt and makes it the accepted
attempt for the READY representation. A forced reparse with identical complete
identities creates a `CONVERGED` attempt whose objects may content-address to the same
bytes. A valid difference creates a `DIVERGED` attempt with its own complete evidence;
it remains reachable but cannot replace the accepted attempt or advance the head.

## RichRepresentationArtifacts

Catalog aggregate joining:

- existing READY `DocumentRepresentation` and zero F002 blocks;
- accepted canonical parse-attempt identifier;
- accepted attempt descriptor, provider-native JSON, F006 native-record and bundle;
- complete ordered rich evidence rows for the accepted attempt;
- creation time and projection count.

A representation is a rich READY aggregate only if every required row and object is
present in one catalog snapshot. Text READY aggregates have no rich-artifact row and
retain current behavior.

## RichIngestionResult

Bounded CLI/service result:

- representation scope;
- disposition and parser/cache flags;
- head advancement;
- native representation and native artifact IDs;
- evidence count and warning codes;
- forced-reparse convergence classification;
- parse-attempt identifier and accepted-attempt identifier;
- ingest timestamp.

It exposes no document body, local path or native payload.

## State transitions

The existing representation lifecycle remains:

```text
missing/FAILED/expired STAGING
             |
             v acquire fenced lease
          STAGING
          /     \
   failure       atomic rich commit
      v                 v
    FAILED            READY
                         |
                         +--> verified CACHE_HIT
```

Initial READY publication includes the base representation, canonical attempt, accepted
rich-artifact link, evidence rows, head update and ingest event in one transaction.
Forced reparses append a complete converged/diverged attempt and event atomically but
never mutate the accepted link. CAS objects published before a failed transaction may be
unreachable but are immutable and never visible as a complete attempt or READY aggregate.
