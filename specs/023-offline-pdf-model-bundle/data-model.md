# Data Model: Offline PDF Model Bundle

## Model source lock

`PdfModelSourceLock` is committed canonical JSON with a format version, compatible Docling/provider profile, aggregate
limits, reviewed sources and a sorted closed file mapping.

`PdfModelSource` fields:

| Field | Rule |
|---|---|
| `repository_id` | fixed `owner/name` identifier from the supported host allowlist |
| `requested_revision` | full lowercase hexadecimal immutable revision |
| `resolved_revision` | must equal the requested revision returned by source metadata |
| `license_id` | reviewed bounded SPDX/license-reference assertion |
| `license_evidence_url` | fixed HTTPS review reference; never fetched offline |

`PdfModelSourceFile` fields:

| Field | Rule |
|---|---|
| `repository_id`, `revision` | reference exactly one locked source |
| `source_path` | traversal-free repository-relative POSIX path |
| `destination_path` | unique, sorted, traversal-free path below `assets/` |
| `sha256`, `byte_length` | exact downloaded bytes; included in aggregate limits |
| `license_id` | equals the referenced reviewed source assertion |

The lock identity is RFC 8785/SHA-256 over the complete canonical document.

## Installed bundle

```text
INSTALL_ROOT/
├── manifest.json
├── provenance.json
├── THIRD_PARTY_NOTICES.md
├── licenses/
│   ├── Apache-2.0.txt
│   └── CDLA-Permissive-2.0.txt
└── assets/
    ├── docling-project--docling-layout-heron/...
    └── docling-project--docling-models/model_artifacts/tableformer/accurate/...
```

`manifest.json` is the existing `ModelBundleManifest`. Its sorted files are relative to `assets/`, and `bundle_id` is the
existing path-independent canonical identity. `provenance.json` binds source-lock identity, bundle ID, exact source
mappings and license-text digests without creation time or host paths. The full installation validator accepts exactly
these fixed control files plus the manifest-listed runtime files.

## Portable package

`PdfBundlePackageManifest` is derived, never separately trusted. It records ZIP profile, bundle/source-lock IDs, every
member's uncompressed SHA-256/length and the package SHA-256/length computed after deterministic construction. The
package identity is its exact file SHA-256.

Members have one closed top-level prefix, unique NFC-normalized case-sensitive POSIX paths, fixed timestamp/mode and
regular-file type. Every member uses `ZIP_STORED`; compressed/encrypted members are rejected.

## Provisioning result

`PdfBundleProvisionResult` contains source-lock ID, bundle ID, payload/file counts, downloaded bytes, installed bytes,
package bytes if produced, duration buckets and closed outcome. It excludes destination/cache paths, URLs with query
parameters, credentials and response bodies.

Lifecycle:

```text
source lock
  -> disjoint staging
  -> each file downloaded and verified
  -> manifest/provenance/notices materialized
  -> full installation verified
  -> atomic publish

any failure -> staging remains unaccepted/removed; destination absent
```

## Benchmark evidence

`PdfBundleObservation` binds protocol, bundle, package, fixture and environment IDs to one closed group:

- `inventory`: counts and logical bytes;
- `package`: deterministic digest/size and install reconciliation;
- `validation`: wall/CPU/RSS samples and tamper judgments;
- `conversion`: cold/warm wall/CPU/RSS, status, native bytes, projection/page counts;
- `offline`: cache emptiness and network-attempt count;
- `correctness`: source/native/evidence identities and anchor/determinism judgments.

`PdfBundleDecision` has closed outcome `PDF_OFFLINE_READY` or `PDF_OFFLINE_NOT_READY`, exact input IDs, all policy checks
and limitations. Markdown is a deterministic projection, never authority.
