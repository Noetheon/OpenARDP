# OpenARDP interchange schemas

This directory contains two independently governed JSON Schema Draft 2020-12
families. The original F002 roots remain schema release `0.1.0`; F006 adds experimental
evidence contract `0.1.0`. The Pydantic models under `src/openardp/domain/` are the
executable authoring source; committed schemas are the provider-neutral interchange
source that other implementations can consume without importing Python.

## Public roots and traceability

| Record | Python model | Schema | Golden fixture | Version field |
|---|---|---|---|---|
| Document Manifest | `DocumentManifest` | `manifest.schema.json` | `tests/fixtures/domain/manifest.json` | `spec_version` |
| Content Block | `ContentBlock` | `block.schema.json` | `tests/fixtures/domain/block.json` | `schema_version` |
| Derivation Record | `DerivationRecord` | `derivation.schema.json` | `tests/fixtures/domain/derivation.json` | `schema_version` |
| Relation | `Relation` | `relation.schema.json` | `tests/fixtures/domain/relation.json` | `schema_version` |
| Context Bundle | `ContextBundle` | `context-bundle.schema.json` | `tests/fixtures/domain/context-bundle.json` | `schema_version` |

Each row is exercised by a positive schema/model round-trip, unknown-field rejection, all three version-failure categories and the record-specific negative tests under `tests/domain/` and `tests/contract/`.

### Experimental evidence roots

| Record | Python model | Schema | Golden fixture | Version field |
|---|---|---|---|---|
| Native Representation | `NativeRepresentation` | `native-representation.schema.json` | `conformance/evidence/v0.1.0/valid/native-representation.json` | `contract_version` |
| Evidence Reference | `EvidenceReference` | `evidence-reference.schema.json` | `conformance/evidence/v0.1.0/valid/evidence-reference-text.json` | `contract_version` |
| Evidence Projection | `EvidenceProjection` | `evidence-projection.schema.json` | `conformance/evidence/v0.1.0/valid/evidence-projection.json` | `contract_version` |
| Trust Classification | `TrustClassification` | `trust-classification.schema.json` | `conformance/evidence/v0.1.0/valid/trust-classification.json` | `contract_version` |

These roots declare `stability=experimental`, use URI-namespaced extensions, and accept
exactly installed contract release `0.1.0`. Their version does not change the application,
workspace, provider-profile, export-profile, or F002 schema release.

### Feature 008 context roots

| Record | Python model | Schema | Golden fixture | Version field |
|---|---|---|---|---|
| Context Bundle | `ContextBundleV020` | `context-bundle-0.2.0.schema.json` | `tests/fixtures/context/context-bundle-0.2.0.json` | `schema_version` |
| Selection Receipt | `SelectionReceipt` | `selection-receipt.schema.json` | `tests/fixtures/context/selection-receipt.json` | `contract_version` |

The F008 bundle evolves the F002 `ContextBundle` line to release `0.2.0` with
discriminated block/projection provenance and untrusted-data envelopes. The receipt is
an independent experimental `0.1.0` root with its own RFC 8785/SHA-256 identity
projection; identity vectors live in `tests/fixtures/context/`. Both generations are
deterministic; the nine earlier schema files and both earlier vector files remain
byte-identical.

Feature 009 adds no interchange schema, identity vector or workspace migration. Its
experimental `MCP interface 0.1.0` is an application contract documented under the
feature and pinned by canonical protocol fixtures. All eleven generated schema files
and all three identity-vector files therefore remain byte-identical to Feature 008.

### Feature 011 visual root

| Record | Python model | Schema | Golden fixture | Version field |
|---|---|---|---|---|
| Visual Evidence Descriptor | `VisualEvidenceDescriptor` | `visual-evidence-descriptor.schema.json` | `tests/fixtures/visual/contract/valid-descriptor.json` | `contract_version` |

F011 adds this single experimental `0.1.0` root without changing the eleven prior
schemas. It composes accepted F006 anchors, exact source/native/projection identities,
a deterministic page-raster recipe, integer crop transform, untrusted-data
classification and a trusted local/export usage policy. Raster records and catalog
rows remain internal runtime contracts.

## Compatibility policy

- Readers accept exactly the explicitly installed schema release `0.1.0`; they do not guess compatibility from a shared minor number.
- A malformed semantic version, a well-formed but uninstalled version and an unsupported major family produce distinct model errors.
- Core objects are closed. Future experimental data is allowed only under the JSON-valued `extensions` member.
- Adding a direct optional field requires a new reviewed schema release. A new reader may consume older installed records, but an old strict reader need not accept a schema it does not have.
- Schema versions, algorithm versions and identity-envelope versions evolve independently.
- Removing fields, weakening invariants, changing identifier inputs or changing the compatibility guarantee requires an ADR and migration analysis.
- The non-resolving `https://openardp.example/...` values are stable identifiers for this pre-stable contract, not runtime network dependencies.

## Enforcement layers

JSON Schema deliberately expresses only portable structural constraints. Cross-field computation remains in the executable record models, and cross-record graph behavior belongs to a later aggregate or service boundary.

| Invariant | Enforcement layer |
|---|---|
| Required fields, closed objects, enum values and scalar types | Schema and model |
| Hash/UUID syntax, UTC timestamp shape and numeric bounds | Schema and model |
| At least one non-null block payload | Schema and model |
| Content trust role is data and instruction execution is always false | Schema and model |
| `version_id` equals the source SHA-256 | Record model |
| Recomputed representation, block, artifact and relation identities match | Record model |
| Derivation lifecycle is consistent with output integrity | Record model |
| Context usage does not exceed its budget | Record model |
| Every evidence scope is pinned in the same context bundle | Record model |
| Parent block exists in the same representation | Aggregate/service in a later feature |
| Required relation graph properties hold across records | Aggregate/service in F010 |

F006 additionally enforces declared native/reference/projection identities, fixed-point
page and table geometry, bounded opaque pointers, projection/reference scope, trust
anti-escalation, and cross-record source/native binding. The exact layer matrix and
identity allowlists are in
[`specs/006-evidence-contract-foundation/contracts/evidence-contracts.md`](../specs/006-evidence-contract-foundation/contracts/evidence-contracts.md).

Feature 007 consumes these roots unchanged. Its Docling descriptor, rich evidence
bundle, parse-attempt and catalog records are internal runtime contracts, not additional
public interchange schemas. The nine generated schema files and both existing identity
vector families must therefore remain byte-identical across F007.

Schema acceptance alone is therefore not proof of semantic validity. Python consumers must use `openardp.domain.validate_json`; independent implementations must reproduce the record-semantic checks documented in `specs/002-domain-models-schemas/contracts/domain-contracts.md`.

## Deterministic regeneration

Normal tests and check mode never rewrite committed contracts. Generate only as an explicit review action:

```bash
uv run --locked python scripts/generate_schemas.py --write
uv run --locked python scripts/generate_schemas.py --check
```

Output is UTF-8 with LF line endings, two-space indentation, sorted object keys and one trailing newline. It contains no timestamps, host paths or network-derived values. The full tests validate each schema with `Draft202012Validator.check_schema` and compare every committed file byte-for-byte with a fresh in-memory build.
